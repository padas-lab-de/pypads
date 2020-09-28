from abc import ABCMeta
from functools import wraps
from typing import Type

from pydantic import BaseModel

from pypads.app.injections.base_logger import SimpleLogger, LoggerCall
from pypads.app.misc.extensions import ExtendableMixin, Plugin
from pypads.model.logger_model import LoggerModel
from pypads.utils.util import inheritors

actuator_plugins = set()


class Actuator(SimpleLogger, metaclass=ABCMeta):
    category: str = "Actuator"

    def build_call_object(self, _pypads_env, **kwargs):
        return LoggerCall(logging_env=_pypads_env,
                          category="ActuatorLoggerCall", **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return LoggerModel


class IActuators(Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(type=Actuator, *args, **kwargs)
        actuator_plugins.add(self)

    def _get_meta(self):
        """ Method returning information about where the actuator was defined."""
        return self.__module__

    def _get_methods(self):
        return [method_name for method_name in dir(self) if callable(getattr(object, method_name))]


def actuator(f):
    """
    Decorator used to convert a function to a tracked actuator.
    :param f:
    :return:
    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        # self is an instance of the class
        return Actuator(fn=f)(self, *args, **kwargs)

    return wrapper


class PyPadsActuators(IActuators):
    def __init__(self):
        super().__init__()

    @property
    def pypads(self):
        from pypads.app.pypads import get_current_pads
        return get_current_pads()

    @actuator
    def set_random_seed(self, seed=None):
        # Set seed if needed
        if seed is None:
            import random
            # import sys
            # seed = random.randrange(sys.maxsize)
            # Numpy only allows for a max value of 2**32 - 1
            seed = random.randrange(2 ** 32 - 1)
        self.pypads.cache.run_add('seed', seed)

        from pypads.injections.analysis.randomness import set_random_seed
        set_random_seed(seed)


class ActuatorPluginManager(ExtendableMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(plugin_list=actuator_plugins)


pypads_actuators = PyPadsActuators()


def actuators():
    """
    Returns classes of
    :return:
    """
    return inheritors(Actuator)
