import inspect

from pypads.autolog.wrapping.base_wrapper import Context
from pypads.autolog.wrapping.class_wrapping import ClassWrapper
from pypads.autolog.wrapping.function_wrapping import FunctionWrapper
from pypads.autolog.wrapping.module_wrapping import ModuleWrapper


def _add_found_class(mapping):
    from pypads.base import get_current_pads
    get_current_pads().mapping_registry.add_found_class(mapping)


def wrap(wrappee, ctx, mapping):
    """
    Wrap given object with pypads functionality
    :param wrappee:
    :param args:
    :param kwargs:
    :return:
    """
    ctx = Context(ctx)

    if inspect.ismodule(wrappee):
        return ModuleWrapper.wrap(wrappee, ctx, mapping)

    elif inspect.isclass(wrappee):
        return ClassWrapper.wrap(wrappee, ctx, mapping)

    elif inspect.isfunction(wrappee):
        return FunctionWrapper.wrap(wrappee, ctx, mapping)
