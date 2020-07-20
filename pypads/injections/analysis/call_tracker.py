import os
import threading
from collections.__init__ import OrderedDict
from typing import Type

from pydantic import BaseModel

from pypads import logger
from pypads.importext.wrapping.base_wrapper import Context
from pypads.model.metadata import ModelInterface, ModelHolder
from pypads.model.models import FunctionReferenceModel, CallAccessorModel, CallIdModel, CallModel


class FunctionReference(ModelInterface):

    def __init__(self, _pypads_context: Context, _pypads_wrappee, *args, **kwargs):
        self.wrappee = _pypads_wrappee
        super().__init__(*args, context=_pypads_context, fn_name=_pypads_wrappee.__name__,
                         **{**{"model_cls": FunctionReferenceModel}, **kwargs})
        self._real_context = None
        self._function_type = None

        if self.is_wrapped():
            self.wrappee = self.context.container.__dict__[self.wrappee.__name__]

    def real_context(self):
        """
        Find where the accessor function was defined
        :return:
        """

        # Return if already found
        if self._real_context:
            return self._real_context
        self._real_context = self.context.real_context(self.wrappee.__name__)
        return self._real_context

    def function_type(self):
        """
        Get the function type of the accessor function.
        :return:
        """

        # Return if already found
        if self._function_type:
            return self._function_type

        if self.context.is_module():
            function_type = "staticmethod"
        else:
            # Get the function type (Method, unbound etc.)
            try:
                real_ctx = self.real_context()
                if real_ctx is None:
                    raise ValueError("Couldn't find real context.")
                function_type = type(real_ctx.get_dict()[self.wrappee.__name__])
            except Exception as e:
                logger.warning("Couldn't get function type of '" + str(self.wrappee.__name__) + "' on '" + str(
                    self.real_context()) + ". Omit logging. " + str(e))
                return None

            # TODO Can we find less error prone ways to get the type of the given fn?
            # Delegate decorator of sklearn obfuscates the real type.
            # if is_package_available("sklearn"):
            #     from sklearn.utils.metaestimators import _IffHasAttrDescriptor
            #     if function_type == _IffHasAttrDescriptor:
            if str(function_type) == "<class 'sklearn.utils.metaestimators._IffHasAttrDescriptor'>":
                function_type = "wrapped"
                self.wrappee = self.real_context().get_dict()[self.wrappee.__name__]

            # Set cached result
            self._function_type = function_type
        return function_type

    def is_static_method(self):
        return "staticmethod" in str(self.function_type())

    def is_function(self):
        return "function" in str(self.function_type())

    def function_name(self):
        return self.wrappee.__name__

    def is_class_method(self):
        return "classmethod" in str(self.function_type())

    def is_wrapped(self):
        return "wrapped" in str(self.function_type())

    @property
    def function_id(self):
        if hasattr(self.wrappee, "__name__"):
            if hasattr(self.context, self.wrappee.__name__):
                return id(getattr(self.context, self.wrappee.__name__))
        return str(id(self.context)) + "." + str(id(self.wrappee))

    def __str__(self):
        return str(self._real_context) + "." + str(self.wrappee.__name__)


class CallAccessor(FunctionReference):

    def __init__(self, *args, instance, _pypads_context, _pypads_wrappee, **kwargs):
        super().__init__(_pypads_context, _pypads_wrappee, instance_id=id(instance),
                         **{**{"model_cls": CallAccessorModel}, **kwargs})
        self._instance = instance

    @property
    def instance(self):
        return self._instance

    @classmethod
    def from_function_reference(cls, function_reference: FunctionReference, instance):
        return CallAccessor(instance=instance, _pypads_context=function_reference.context,
                            _pypads_wrappee=function_reference.wrappee)

    def is_call_identity(self, other):
        if other.is_class_method() or other.is_static_method() or other.is_wrapped():
            if other.context == self.context:
                if other.wrappee.__name__ == self.wrappee.__name__:
                    return True
        if other.is_function():
            if other.instance_id == self.instance_id:
                if other.wrappee.__name__ == self.wrappee.__name__:
                    return True


# class CallMapping(CallAccessor):
#
#     def __init__(self, instance, _pypads_context, _pypads_wrappee, mapping):
#         super().__init__(instance, _pypads_context, _pypads_wrappee)
#         self._mapping = mapping
#
#     @property
#     def mapping(self):
#         return self._mapping

class CallId(CallAccessor):

    def __init__(self, instance, _pypads_context,
                 _pypads_wrappee, instance_number, call_number, **kwargs):
        super().__init__(instance=instance, _pypads_context=_pypads_context, _pypads_wrappee=_pypads_wrappee,
                         process=os.getpid(), thread=threading.get_ident(),
                         instance_number=instance_number, call_number=call_number,
                         **{**{"model_cls": CallIdModel}, **kwargs})

    @classmethod
    def from_accessor(cls, accessor: CallAccessor, instance_number, call_number):
        return CallId(accessor.instance, accessor.context, accessor.wrappee, instance_number, call_number)

    def to_parent_folder(self):
        return os.path.join("process_" + str(self.process) + str(self.thread))

    def to_folder(self):
        return os.path.join(*self.to_fragements())

    def __str__(self):
        return ".".join(self.to_fragements())

    def to_fragements(self):
        return ("process_" + str(self.process), "thread_" + str(self.thread),
                "context_" + self.context.container.__name__,
                "instance_" + str(
                    self.instance_number), "function_" + self.wrappee.__name__, "call_" + str(self.call_number))


class Call(ModelHolder):

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return CallModel

    def __init__(self, call_id: CallId, *args, **kwargs):
        super().__init__(*args, call_id=call_id, **kwargs)
        self._active_hooks = set()

    def finish(self):
        self.finished = True

    def add_hook(self, hook):
        self._active_hooks.add(hook)

    def has_hook(self, hook):
        return hook in self._active_hooks

    def remove_hook(self, hook):
        self._active_hooks.remove(hook)

    def to_folder(self):
        return self.call_id.to_folder()


class LoggingEnv:

    def __init__(self, parameter, experiment_id, run_id):
        self._parameter = parameter
        self._experiment_id = experiment_id
        self._run_id = run_id
        from pypads.app.pypads import get_current_pads
        self._pypads = get_current_pads()

    @property
    def experiment_id(self):
        return self._experiment_id

    @property
    def run_id(self):
        return self._run_id

    @property
    def parameter(self):
        return self._parameter

    @property
    def pypads(self):
        return self._pypads


class InjectionLoggingEnv(LoggingEnv):

    def __init__(self, mappings, hook, callback, call: Call, parameter, experiment_id, run_id):
        super().__init__(parameter, experiment_id, run_id)
        self._call = call
        self._callback = callback
        self._hook = hook
        self._mappings = mappings

    @property
    def call(self):
        return self._call

    @property
    def callback(self):
        return self._callback

    @property
    def hook(self):
        return self._hook

    @property
    def mappings(self):
        return self._mappings


class CallTracker:
    """
    This class tracks the number of execution per instance of an object.
    """

    def __init__(self, pads):
        self._pads = pads
        self._call_stack = []

    def instance_call_number(self, accessor):
        function_calls: OrderedDict = self.function_call_dict(accessor.function_id)
        instance_id = accessor.instance_id

        call_items = list(function_calls.items())
        for instance_number in range(0, len(call_items)):
            # noinspection PyUnresolvedReferences
            key, value = call_items[instance_number]
            if key == instance_id:
                return instance_number
        return 0

    @property
    def call_stack(self):
        return self._call_stack

    def call_depth(self):
        return len(self._call_stack)

    def call_number(self, accessor: CallAccessor):
        """
        Get the number of calls of given call accessor
        :param accessor:
        :return:
        """
        return len(self.calls(accessor))

    def make_call_id(self, accessor: CallAccessor) -> CallId:
        """
        Returns the current call id. The id is built from: process_id, thread_id, defining_ctx_name, self_number/id,
        wrapped_fn_name, call_number
        :param accessor:
        :return:
        """
        return CallId(accessor.instance, accessor.context, accessor.wrappee, self.instance_call_number(accessor),
                      self.call_number(accessor))

    def current_call_number(self):
        """
        Get the current call number
        :return:
        """
        call = self._call_stack[-1]
        return self.call_number(call.accessor)

    def current_call(self):
        """
        Get the call_id of the current call
        :return:
        """
        return self._call_stack[-1] if len(self._call_stack) > 0 else None

    def current_process(self):
        return str(self._call_stack[-1].call_id.process) + "." + str(self._call_stack[-1].call_id.thread)

    def call_objects(self):
        """
        Get all call objects which are stored in our tracker.
        :return:
        """
        # Add call_objects if not exists in cache
        if not self._pads.cache.run_exists("call_objects"):
            self._pads.cache.run_add("call_objects", {})
        return self._pads.cache.run_get("call_objects")

    def function_call_dict(self, function_id) -> OrderedDict:
        call_objects = self.call_objects()
        if function_id not in call_objects:
            call_objects[function_id] = OrderedDict()
        return call_objects[function_id]

    def calls(self, accessor: CallAccessor):
        """
        Get all calls of given call accessor.
        :param accessor:
        :return:
        """
        instance_id = accessor.instance_id
        function_id = accessor.function_id

        function_calls = self.function_call_dict(function_id)
        if instance_id not in function_calls:
            function_calls[instance_id] = []

        return function_calls[instance_id]

    def has_call_identity(self, accessor: CallAccessor):
        for stored in self._call_stack:
            if stored.is_call_identity(accessor):
                return True
        return False

    def add(self, call: Call):
        """
        When a new call is triggered execute that function. This should be the first logging function called in each
        logging function stack.
        :return: A dict for holding information about the call.
        """
        self._call_stack.append(call)

        calls = self.calls(call.call_id)
        calls.append(call)
        return call

    def finish(self, call):
        if call in self._call_stack:
            call.finish()
            self._call_stack.remove(call)
            # TODO clear memory in call_objects?
        else:
            logger.error("Tried to finish call which is not on the stack. " + str(call))


def add_call(accessor):
    from pypads.app.pypads import get_current_pads
    pads = get_current_pads()
    call = Call(call_id=pads.call_tracker.make_call_id(accessor))
    return pads.call_tracker.add(call)


def finish_call(call):
    from pypads.app.pypads import get_current_pads
    pads = get_current_pads()
    return pads.call_tracker.finish(call)
