from abc import abstractmethod, ABCMeta

from pypads import logger
from pypads.app.injections.base_logger import RunLoggerFunction
from pypads.app.misc.mixins import BaseDefensiveCallableMixin, ConfigurableCallableMixin
# Default init_run fns
from pypads.utils.util import inheritors


class BaseRunLogger(RunLoggerFunction, BaseDefensiveCallableMixin, ConfigurableCallableMixin):
    """
    Base run logger. This function is to be called after or before a mlflow run.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, fn=None, **kwargs):
        super().__init__(*args, fn=fn, **kwargs)
        if self._fn is None:
            self._fn = self._call

    @property
    def __name__(self):
        if hasattr(self, "_fn") and self._fn is not self._call:
            return self._fn.__name__
        else:
            return self.__class__.__name__

    @abstractmethod
    def _call(self, pads, *args, **kwargs):
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
