from _py_abc import ABCMeta
from abc import abstractmethod

from pypads.functions.loggers.base_logger import DependencyMixin


class RunInitLoggingFunction(DependencyMixin):
    __metaclass__ = ABCMeta
    """
    This class should be used to define new loggers
    """

    def __init__(self, **static_parameters):
        self._static_parameters = static_parameters

    def __call__(self, pads, *args, **kwargs):
        self._call(pads, *args, **{**self._static_parameters, **kwargs})

    @abstractmethod
    def _call(self, pads, *args, **kwargs):
        pass
