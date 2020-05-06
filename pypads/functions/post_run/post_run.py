from abc import ABCMeta, abstractmethod

from pypads.functions.loggers.base_logger import FunctionHolder
from pypads.functions.loggers.mixins import DependencyMixin, OrderMixin, IntermediateCallableMixin, TimedCallableMixin


class PostRunFunction(IntermediateCallableMixin, FunctionHolder, TimedCallableMixin, DependencyMixin, OrderMixin):
    __metaclass__ = ABCMeta
    """
    This class should be used to define new post run functions
    """

    @abstractmethod
    def __init__(self, *args, fn=None, **kwargs):
        super().__init__(*args, fn=fn, **kwargs)
        if self._fn is None:
            self._fn = self._call

    @abstractmethod
    def _call(self, pads, *args, **kwargs):
        return NotImplementedError()

    def __real_call__(self, *args, **kwargs):
        from pypads.pypads import get_current_pads
        return super().__real_call__(get_current_pads(), *args, **kwargs)
