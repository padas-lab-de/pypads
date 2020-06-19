from abc import ABCMeta
from functools import wraps

from pypads.app.injections.base_logger import FunctionHolder
from pypads.app.misc.extensions import ExtendableMixin, Plugin
from pypads.utils.util import inheritors

actuator_plugins = set()


class Actuator(FunctionHolder, metaclass=ABCMeta):

    def __init__(self, *args, fn, **kwargs):
        super().__init__(*args, fn=fn, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.__real_call__(*args, **kwargs)


class IActuators(Plugin):

    def __init__(self):
        super().__init__(type=Actuator)
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


class PypadsActuators(IActuators):
    def __init__(self, pypads):
        self._pypads = pypads
        super().__init__()

    @actuator
    def set_random_seed(self, seed=None):
        # Set seed if needed
        if seed is None:
            import random
            # import sys
            # seed = random.randrange(sys.maxsize)
            # Numpy only allows for a max value of 2**32 - 1
            seed = random.randrange(2 ** 32 - 1)
        self._pypads.cache.run_add('seed', seed)

        from pypads.injections.analysis.randomness import set_random_seed
        set_random_seed(seed)


class ActuatorPluginManager(ExtendableMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(instances=PypadsActuators(*args, **kwargs))


def actuators():
    """
    Returns classes of
    :return:
    """
    return inheritors(Actuator)
