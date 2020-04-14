import inspect
from types import ModuleType

from pypads.autolog.wrapping.base_wrapper import Context
from pypads.autolog.wrapping.class_wrapping import ClassWrapper
from pypads.autolog.wrapping.function_wrapping import FunctionWrapper
from pypads.autolog.wrapping.module_wrapping import ModuleWrapper


def _add_found_class(mapping):
    from pypads.pypads import get_current_pads
    get_current_pads().mapping_registry.add_found_class(mapping)


def wrap(wrappee, ctx, mapping):
    """
    Wrap given object with pypads functionality
    :param wrappee:
    :param args:
    :param kwargs:
    :return:
    """
    if not str(wrappee).startswith("_pypads"):
        if not isinstance(ctx, Context):
            try:
                ctx = Context(ctx)
            except ValueError as e:

                dummy = ModuleType("dummy_module")
                if inspect.isfunction(wrappee):
                    setattr(dummy, wrappee.__name__, wrappee)
                ctx = Context(dummy)

        if inspect.ismodule(wrappee):
            return ModuleWrapper.wrap(wrappee, ctx, mapping)

        elif inspect.isclass(wrappee):
            return ClassWrapper.wrap(wrappee, ctx, mapping)

        elif inspect.isfunction(wrappee):
            return FunctionWrapper.wrap(wrappee, ctx, mapping)
    else:
        return wrappee
