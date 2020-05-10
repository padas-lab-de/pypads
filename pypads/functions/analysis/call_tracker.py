import os
import threading
from collections.__init__ import OrderedDict

from pypads import logger
from pypads.autolog.wrapping.base_wrapper import Context


class FunctionReference:

    def __init__(self, _pypads_context: Context, _pypads_wrappee):
        self._context = _pypads_context
        self._function = _pypads_wrappee
        self._real_context = None
        self._function_type = None

        if self.is_wrapped():
            self._function = self.context.container.__dict__[self._function.__name__]

    @property
    def context(self):
        return self._context

    @property
    def wrappee(self):
        return self._function

    def real_context(self):
        """
        Find where the accessor function was defined
        :return:
        """

        # Return if already found
        if self._real_context:
            return self._real_context
        self._real_context = self._context.real_context(self._function.__name__)
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
                function_type = type(real_ctx.get_dict()[self._function.__name__])
            except Exception as e:
                logger.warning("Couldn't get function type of '" + str(self._function.__name__) + "' on '" + str(
                    self.real_context()) + ". Omit logging. " + str(e))
                return None

            # TODO Can we find less error prone ways to get the type of the given fn?
            # Delegate decorator of sklearn obfuscates the real type.
            # if is_package_available("sklearn"):
            #     from sklearn.utils.metaestimators import _IffHasAttrDescriptor
            #     if function_type == _IffHasAttrDescriptor:
            if str(function_type) == "<class 'sklearn.utils.metaestimators._IffHasAttrDescriptor'>":
                function_type = "wrapped"
                self._function = self.real_context().get_dict()[self._function.__name__]

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


class CallAccessor(FunctionReference):

    def __init__(self, instance, _pypads_context, _pypads_wrappee):
        super().__init__(_pypads_context, _pypads_wrappee)
        self._instance = instance

    @property
    def instance(self):
        return self._instance

    @property
    def instance_id(self):
        return id(self.instance)

    @classmethod
    def from_function_reference(cls, function_reference: FunctionReference, instance):
        return CallAccessor(instance, function_reference.context, function_reference.wrappee)

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
                 _pypads_wrappee, instance_number, call_number):
        super().__init__(instance, _pypads_context, _pypads_wrappee)
        self._process = os.getpid()
        self._thread = threading.get_ident()
        self._instance_number = instance_number
        self._call_number = call_number

    @classmethod
    def from_accessor(cls, accessor: CallAccessor, instance_number, call_number):
        return CallId(accessor.instance, accessor.context, accessor.wrappee, instance_number, call_number)

    @property
    def process(self):
        return self._process

    @property
    def thread(self):
        return self._thread

    @property
    def instance_number(self):
        return self._instance_number

    @property
    def call_number(self):
        return self._call_number

    def to_parent_folder(self):
        return os.path.join("process_" + str(self._process) + str(self._thread))

    def to_folder(self):
        return os.path.join(*self.to_fragements())

    def __str__(self):
        return ".".join(self.to_fragements())

    def to_fragements(self):
        return ("process_" + str(self._process), "thread_" + str(self._thread),
                "context_" + self.context.container.__name__,
                "instance_" + str(
                    self.instance_number), "function_" + self.wrappee.__name__, "call_" + str(self._call_number))


class Call:

    def __init__(self, call_id: CallId):
        self._call_id = call_id
        self._finished = False
        self._active_hooks = set()

    @property
    def call_id(self):
        return self._call_id

    @property
    def finished(self):
        return self._finished

    @property
    def active_hooks(self):
        return self._active_hooks

    def finish(self):
        self._finished = True

    def add_hook(self, hook):
        self._active_hooks.add(hook)

    def has_hook(self, hook):
        return hook in self._active_hooks

    def remove_hook(self, hook):
        self._active_hooks.remove(hook)

    def __str__(self):
        return self.call_id.__str__()

    def to_folder(self):
        return self.call_id.to_folder()

    # def __getstate__(self):
    #     """
    #     Overwrite standard pickling by excluding the functions
    #     :return:
    #     """
    #     # can't pickle call_ids here
    #     self.call_id_fragments = str(self.call_id.to_fragements())
    #     state = self.__dict__.copy()
    #     del state["_call_id"]
    #     return state
    #
    # def __setstate__(self, state):
    #     self.__dict__.update(state)
    #     state["_call_id"] = None
    #     # can we rebuild call_id?
    #     return state


class LoggingEnv:

    def __init__(self, mapping, hook, parameter, callback, call: Call):
        self._call = call
        self._callback = callback
        self._hook = hook
        self._mapping = mapping
        self._parameter = parameter

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
    def mapping(self):
        return self._mapping

    @property
    def parameter(self):
        return self._parameter


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
    from pypads.pypads import get_current_pads
    pads = get_current_pads()
    call = Call(pads.call_tracker.make_call_id(accessor))
    return pads.call_tracker.add(call)


def finish_call(call):
    from pypads.pypads import get_current_pads
    pads = get_current_pads()
    return pads.call_tracker.finish(call)
