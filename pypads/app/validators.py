from abc import ABCMeta
from functools import wraps

from pypads.app.injections.base_logger import LoggerFunction
from pypads.app.misc.extensions import ExtendableMixin, Plugin
from pypads.injections.analysis.determinism import check_determinism
from pypads.utils.util import inheritors

validator_plugins = set()


class Validator(LoggerFunction, metaclass=ABCMeta):

    def __init__(self, *args, fn, **kwargs):
        super().__init__(*args, fn=fn, **kwargs)

    def __call__(self, *args, **kwargs):
        # TODO validator call
        return self.__real_call__(*args, **kwargs)


class IValidators(Plugin):

    def __init__(self):
        super().__init__(type=Validator)
        validator_plugins.add(self)

    def _get_meta(self):
        """ Method returning information about where the actuator was defined."""
        return self.__module__

    def _get_methods(self):
        return [method_name for method_name in dir(self) if callable(getattr(object, method_name))]


def validator(f):
    """
    Validator used to convert a function to a tracked actuator.
    :param f:
    :return:
    """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        # self is an instance of the class
        return Validator(fn=f)(self, *args, **kwargs)

    return wrapper


class PyPadsValidators(IValidators):
    def __init__(self):
        super().__init__()

    @property
    def pypads(self):
        from pypads.app.pypads import get_current_pads
        return get_current_pads()

    @validator
    def determinism(self):
        check_determinism()


class ValidatorPluginManager(ExtendableMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(plugin_list=validator_plugins)


pypads_validators = PyPadsValidators()


def validators():
    """
    Returns classes of
    :return:
    """
    return inheritors(Validator)
