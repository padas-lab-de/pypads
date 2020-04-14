from abc import ABCMeta, abstractmethod

from pypads.functions.loggers.base_logger import FunctionHolder
from pypads.functions.loggers.mixins import DependencyMixin, OrderMixin, IntermediateCallableMixin


class PostRunFunction(IntermediateCallableMixin, FunctionHolder, DependencyMixin, OrderMixin):
    __metaclass__ = ABCMeta
    """
    This class should be used to define new post run functions
    """

    @abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
