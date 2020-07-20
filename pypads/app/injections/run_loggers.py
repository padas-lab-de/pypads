from abc import abstractmethod, ABCMeta

from pydantic.main import BaseModel
from pydantic.networks import HttpUrl
from typing import Type

from pypads import logger
from pypads.app.injections.base_logger import LoggerFunction
from pypads.app.misc.mixins import BaseDefensiveCallableMixin, ConfigurableCallableMixin, OrderMixin
# Default init_run fns
from pypads.injections.analysis.call_tracker import LoggingEnv
from pypads.model.models import RunLoggerModel
from pypads.utils.util import inheritors


class RunLoggerFunction(LoggerFunction, OrderMixin, metaclass=ABCMeta):
    is_a: HttpUrl = "https://www.padre-lab.eu/onto/run-logger"

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return RunLoggerModel


class BaseRunLogger(RunLoggerFunction, BaseDefensiveCallableMixin, ConfigurableCallableMixin):
    """
    Base run logger. This function is to be called after or before a mlflow run.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def __name__(self):
        if hasattr(self, "_fn") and self._fn is not self._call:
            return self._fn.__name__
        else:
            return self.__class__.__name__

    @abstractmethod
    def _call(self, _pypads_env: LoggingEnv, *args, **kwargs):
        """
        Function where to add you custom code to execute before starting or ending the run.

        :param pads: the current instance of PyPads.
        """
        return NotImplementedError()


class RunSetupFunction(BaseRunLogger, metaclass=ABCMeta):
    """
    This class should be used to define new pre run functions
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __real_call__(self, *args, **kwargs):
        from pypads.app.pypads import get_current_pads
        logger.debug("Called pre run function " + str(self))
        return super().__real_call__(get_current_pads(), *args, **kwargs)


class RunTeardownFunction(BaseRunLogger, metaclass=ABCMeta):
    """
    This class should be used to define new post run functions
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __real_call__(self, *args, **kwargs):
        from pypads.app.pypads import get_current_pads
        logger.debug("Called post run function " + str(self))
        return super().__real_call__(get_current_pads(), *args, **kwargs)


def run_setup_functions():
    """
    Find all pre run functions defined in our imported context.
    :return:
    """
    return inheritors(RunSetupFunction)


def run_teardown_functions():
    """
    Find all post run functions defined in our imported context.
    :return:
    """
    return inheritors(RunTeardownFunction)
