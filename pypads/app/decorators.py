from abc import ABCMeta
from functools import wraps
from typing import List

from pypads.app.env import LoggerEnv
from pypads.app.misc.extensions import ExtendableMixin, Plugin
from pypads.app.misc.mixins import FunctionHolderMixin
from pypads.importext.mappings import Mapping
from pypads.utils.util import inheritors, get_class_that_defined_method, get_experiment_id, get_run_id

decorator_plugins = set()


class Decorator(FunctionHolderMixin, metaclass=ABCMeta):

    def __init__(self, *args, fn, **kwargs):
        super().__init__(*args, fn=fn, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.__real_call__(*args, **kwargs)


class IDecorators(Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(type=Decorator, *args, **kwargs)
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
        return Decorator(fn=f)(self, *args, _pypads_env=LoggerEnv(parameter=dict(), experiment_id=get_experiment_id(),
                                                                  run_id=get_run_id()), **kwargs)

    return wrapper


class PyPadsDecorators(IDecorators):
    def __init__(self):
        super().__init__()

    @property
    def pypads(self):
        from pypads.app.pypads import get_current_pads
        return get_current_pads()

    # @decorator
    # def project(self, clazz):
    #     """
    #     Used to annotate a data class as a project representation. The data class should define following structure:
    #
    #     @project
    #     class Project:
    #         name = "My project"
    #         description = "We hope to solve something difficult."
    #         hypothesis = "This hypothesis is difficult."
    #     :return:
    #     """
    #     # TODO Write to pypads
    #     self.pypads.api.log_artifact()
    #     return dataclass(clazz)

    @decorator
    def track(self, event="pypads_log", mapping: Mapping = None):
        def track_decorator(fn):
            ctx = get_class_that_defined_method(fn)
            events = event if isinstance(event, List) else [event]
            return self.pypads.api.track(ctx=ctx, fn=fn, anchors=events, mapping=mapping)

        return track_decorator


class DecoratorPluginManager(ExtendableMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(plugin_list=decorator_plugins)


pypads_decorators = PyPadsDecorators()


def decorators():
    """
    Returns classes of
    :return:
    """
    return inheritors(Decorator)
