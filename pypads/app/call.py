import os
import threading
from typing import Type

from pydantic import BaseModel

from pypads import logger
from pypads.importext.wrapping.base_wrapper import Context
from pypads.model.metadata import ModelObject
from pypads.model.models import FunctionReferenceModel, CallAccessorModel, CallIdModel, CallModel


class FunctionReference(ModelObject):

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return FunctionReferenceModel

    def __init__(self, _pypads_context: Context, _pypads_wrappee, *args, **kwargs):
        self.wrappee = _pypads_wrappee
        super().__init__(*args, context=_pypads_context, fn_name=_pypads_wrappee.__name__,
                         **kwargs)
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

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return CallAccessorModel

    def __init__(self, *args, instance, _pypads_context, _pypads_wrappee, **kwargs):
        super().__init__(_pypads_context, _pypads_wrappee, instance_id=id(instance),
                         **kwargs)
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


class CallId(CallAccessor):

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return CallIdModel

    def __init__(self, instance, _pypads_context,
                 _pypads_wrappee, instance_number, call_number, **kwargs):
        super().__init__(instance=instance, _pypads_context=_pypads_context, _pypads_wrappee=_pypads_wrappee,
                         process=os.getpid(), thread=threading.get_ident(),
                         instance_number=instance_number, call_number=call_number,
                         **kwargs)

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


class Call(ModelObject):

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
