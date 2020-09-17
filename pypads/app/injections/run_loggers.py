from abc import ABCMeta
from typing import Type

from pydantic.main import BaseModel
from pydantic.networks import HttpUrl

# Default init_run fns
from pypads import logger
from pypads.app.injections.base_logger import LoggerCall, SimpleLogger
from pypads.app.misc.mixins import OrderMixin
from pypads.arguments import ontology_uri
from pypads.model.logger_model import RunLoggerModel
from pypads.utils.util import inheritors


class RunLogger(SimpleLogger, OrderMixin, metaclass=ABCMeta):
    is_a: HttpUrl = f"{ontology_uri}run-logger"

    def build_call_object(self, _pypads_env, **kwargs):
        return LoggerCall(logging_env=_pypads_env, is_a=f"{ontology_uri}RunLoggerCall", **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return RunLoggerModel

    def _base_path(self):
        return "RunLoggers/"


class RunSetup(RunLogger, metaclass=ABCMeta):
    """
    This class should be used to define new pre run functions
    """
    is_a: HttpUrl = f"{ontology_uri}runsetup-logger"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __real_call__(self, *args, **kwargs):
        logger.debug("Called pre run function " + str(self))
        return super().__real_call__(*args, **kwargs)

    def _base_path(self):
        return super()._base_path() + "Setup/{}/".format(self.__name__)


class RunTeardown(RunLogger, metaclass=ABCMeta):
    """
    This class should be used to define new post run functions
    """
    is_a: HttpUrl = f"{ontology_uri}runteardown-logger"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __real_call__(self, *args, **kwargs):
        logger.debug("Called post run function " + str(self))
        return super().__real_call__(*args, **kwargs)

    def _base_path(self):
        return super()._base_path() + "Teardown/{}/".format(self.__name__)


def run_setup_functions():
    """
    Find all pre run functions defined in our imported context.
    :return:
    """
    return inheritors(RunSetup)


def run_teardown_functions():
    """
    Find all post run functions defined in our imported context.
    :return:
    """
    return inheritors(RunTeardown)
