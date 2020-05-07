from abc import ABCMeta, abstractmethod

from pypads.functions.loggers.base_logger import FunctionHolder
from pypads.functions.loggers.mixins import DependencyMixin, OrderMixin, IntermediateCallableMixin


class PostRunFunction(IntermediateCallableMixin, FunctionHolder, DependencyMixin, OrderMixin):
    """
    This class should be used to define new post run functions
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abstractmethod
    def _call(self, pads, *args, **kwargs):
        """
        Function where to add you custom code to execute after ending the run.

        :param pads: the current instance of PyPads.
        """
        pass

    def __real_call__(self, *args, **kwargs):
        from pypads.pypads import get_current_pads
        return self._call(get_current_pads(), *args, **kwargs)
