from abc import ABCMeta
from functools import wraps
from typing import List

from pypads.app.injections.base_logger import FunctionHolder
from pypads.app.misc.extensions import ExtendableMixin, Plugin
from pypads.importext.mappings import Mapping
from pypads.utils.util import inheritors, get_class_that_defined_method

decorator_plugins = set()


class Decorator(FunctionHolder, metaclass=ABCMeta):

    def __init__(self, *args, fn, **kwargs):
        super().__init__(*args, fn=fn, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.__real_call__(*args, **kwargs)


class IDecorators(Plugin):

    def __init__(self):
        super().__init__(type=Decorator)
        decorator_plugins.add(self)

    def _get_meta(self):
        """ Method returning information about where the actuator was defined."""
        return self.__module__

    def _get_methods(self):
        return [method_name for method_name in dir(self) if callable(getattr(object, method_name))]


def decorator(f):
    """
    Decorator used to convert a function to a tracked actuator.
    :param f:
    :return:
    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        # self is an instance of the class
        return Decorator(fn=f)(self, *args, **kwargs)

    return wrapper


class PyPadsDecorators(IDecorators):
    def __init__(self, pypads):
        self._pypads = pypads
        super().__init__()

    @decorator
    def track(self, event="pypads_log", mapping: Mapping = None):
        def track_decorator(fn):
            ctx = get_class_that_defined_method(fn)
            events = event if isinstance(event, List) else [event]
            return self._pypads.api.track(ctx=ctx, fn=fn, hooks=events, mapping=mapping)

        return track_decorator


class DecoratorPluginManager(ExtendableMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(instances=PyPadsDecorators(*args, **kwargs))


def actuators():
    """
    Returns classes of
    :return:
    """
    return inheritors(Decorator)
