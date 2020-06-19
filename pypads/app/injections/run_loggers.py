from abc import abstractmethod, ABCMeta

from pypads import logger
from pypads.app.injections.base_logger import FunctionHolder
from pypads.app.misc.mixins import DefensiveCallableMixin, IntermediateCallableMixin, TimedCallableMixin, \
    DependencyMixin, OrderMixin, ConfigurableCallableMixin
# Default init_run fns
from pypads.utils.util import inheritors


class BaseDefensiveCallable(DefensiveCallableMixin):
    """
    Defensive callable ignoring errors but printing a warning to console.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, message=None, **kwargs):
        self._message = message if message else "Couldn't execute {}, because of exception: {}"
        super().__init__(*args, **kwargs)

    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        logger.warning(self._message.format(str(self.__name__), str(error)))


class BaseRunLogger(BaseDefensiveCallable, IntermediateCallableMixin, FunctionHolder, TimedCallableMixin,
                    DependencyMixin, OrderMixin, ConfigurableCallableMixin):
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


class PreRunFunction(BaseRunLogger, metaclass=ABCMeta):
    """
    This class should be used to define new pre run functions
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __real_call__(self, *args, **kwargs):
        from pypads.app.pypads import get_current_pads
        logger.debug("Called pre run function " + str(self))
        return super().__real_call__(get_current_pads(), *args, **kwargs)


class PostRunFunction(BaseRunLogger, metaclass=ABCMeta):
    """
    This class should be used to define new post run functions
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __real_call__(self, *args, **kwargs):
        from pypads.app.pypads import get_current_pads
        logger.debug("Called post run function " + str(self))
        return super().__real_call__(get_current_pads(), *args, **kwargs)


def pre_run_functions():
    """
    Find all pre run functions defined in our imported context.
    :return:
    """
    return inheritors(PreRunFunction)


def post_run_functions():
    """
    Find all post run functions defined in our imported context.
    :return:
    """
    return inheritors(PostRunFunction)
