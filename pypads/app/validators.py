from abc import ABCMeta
from functools import wraps
from typing import Type

from pydantic import BaseModel, HttpUrl

from app.env import LoggingEnv
from pypads.app.injections.base_logger import LoggerFunction, LoggingExecutor, LoggerCall
from pypads.app.misc.extensions import ExtendableMixin, Plugin
from pypads.injections.analysis.determinism import check_determinism
from pypads.model.models import LoggerModel
from pypads.utils.util import inheritors

validator_plugins = set()


class Validator(LoggerFunction, metaclass=ABCMeta):
    is_a: HttpUrl = "https://www.padre-lab.eu/onto/validator"

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return LoggerModel

    def __init__(self, *args, fn=None, **kwargs):
        super().__init__(*args, **kwargs)
        if fn is None:
            fn = self._call
        if not hasattr(self, "_fn"):
            self._fn = LoggingExecutor(fn=fn)

    @property
    def __name__(self):
        if hasattr(self, "_fn") and self._fn is not self._call:
            return self._fn.__name__
        else:
            return self.__class__.__name__

    def _call(self, _pypads_env: LoggingEnv, *args, **kwargs):
        """
        Function where to add you custom code to execute before starting or ending the run.

        :param pads: the current instance of PyPads.
        """
        pass

    def __real_call__(self, *args, _pypads_env: LoggingEnv, **kwargs):
        self.store_schema()

        _pypads_params = _pypads_env.parameter

        logger_call = LoggerCall(created_by=self.model(), is_a="https://www.padre-lab.eu/onto/ValidatorCall",
                                 logging_env=_pypads_env)

        _return, time = self._fn(*args, _pypads_env=_pypads_env, _logger_call=logger_call,
                                 _pypads_params=_pypads_params,
                                 **kwargs)

        logger_call.execution_time = time
        logger_call.store()
        return _return


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
