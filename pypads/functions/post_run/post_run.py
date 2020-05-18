from abc import ABCMeta, abstractmethod

from pypads import logger
from pypads.functions.loggers.base_logger import FunctionHolder
from pypads.functions.loggers.mixins import DependencyMixin, OrderMixin, IntermediateCallableMixin, TimedCallableMixin, \
    DefensiveCallableMixin


class PostRunFunction(DefensiveCallableMixin, IntermediateCallableMixin, FunctionHolder, TimedCallableMixin,
                      DependencyMixin, OrderMixin):
    """
    This class should be used to define new post run functions
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, fn=None, **kwargs):
        super().__init__(*args, fn=fn, **kwargs)
        if self._fn is None:
            self._fn = self._call

    @property
    def __name__(self):
        if self._fn is not self._call:
            return self._fn.__name__
        else:
            return self.__class__.__name__

    @abstractmethod
    def _call(self, pads, *args, **kwargs):
        """
        Function where to add you custom code to execute after ending the run.

        :param pads: the current instance of PyPads.
        """
        return NotImplementedError()

    def __real_call__(self, *args, **kwargs):
        from pypads.pypads import get_current_pads
        logger.debug("Called post run function " + str(self))
        return super().__real_call__(get_current_pads(), *args, **kwargs)

    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        logger.warning("Couldn't execute " + self.__name__ + ", because of exception: " + str(error))
