import inspect
from types import ModuleType
from typing import Set

from pypads.importext.mappings import MatchedMapping
from pypads.importext.wrapping.base_wrapper import Context
from pypads.importext.wrapping.class_wrapping import ClassWrapper
from pypads.importext.wrapping.function_wrapping import FunctionWrapper
from pypads.importext.wrapping.module_wrapping import ModuleWrapper


def _add_found_class(mapping):
    from pypads.app.pypads import get_current_pads
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

    def wrap(self, wrappee, ctx, matched_mappings: Set[MatchedMapping]):
        """
        Wrap given object with pypads functionality
        :param ctx:
        :param matched_mappings:
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
                return self._module_wrapper.wrap(wrappee, ctx, matched_mappings)

            elif inspect.isclass(wrappee):
                return self._class_wrapper.wrap(wrappee, ctx, matched_mappings)

            elif inspect.isfunction(wrappee):
                return self._function_wrapper.wrap(wrappee, ctx, matched_mappings)
        else:
            return wrappee
