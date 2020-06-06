import inspect
from types import ModuleType

from pypads.autolog.mappings import MappingHit
from pypads.autolog.wrapping.base_wrapper import Context
from pypads.autolog.wrapping.class_wrapping import ClassWrapper
from pypads.autolog.wrapping.function_wrapping import FunctionWrapper
from pypads.autolog.wrapping.module_wrapping import ModuleWrapper


def _add_found_class(mapping):
    from pypads.pypads import get_current_pads
    get_current_pads().mapping_registry.add_found_class(mapping)


class WrapManager:

    def __init__(self, pypads):
        self._pypads = pypads
        self._module_wrapper = ModuleWrapper(pypads)
        self._class_wrapper = ClassWrapper(pypads)
        self._function_wrapper = FunctionWrapper(pypads)

    @property
    def module_wrapper(self):
        return self._module_wrapper

    @property
    def class_wrapper(self):
        return self._class_wrapper

    @property
    def function_wrapper(self):
        return self._function_wrapper

    def wrap(self, wrappee, ctx, mapping_hit: MappingHit):
        """
        Wrap given object with pypads functionality
        :param wrappee:
        :param args:
        :param kwargs:
        :return:
        """
        if not str(wrappee).startswith("_pypads") and not str(wrappee).startswith("__"):
            if not isinstance(ctx, Context):
                try:
                    ctx = Context(ctx)
                except ValueError as e:

                    dummy = ModuleType("dummy_module")
                    if inspect.isfunction(wrappee):
                        setattr(dummy, wrappee.__name__, wrappee)
                    ctx = Context(dummy)

            if inspect.ismodule(wrappee):
                return self._module_wrapper.wrap(wrappee, ctx, mapping_hit)

            elif inspect.isclass(wrappee):
                return self._class_wrapper.wrap(wrappee, ctx, mapping_hit)

            elif inspect.isfunction(wrappee):
                return self._function_wrapper.wrap(wrappee, ctx, mapping_hit)
        else:
            return wrappee
