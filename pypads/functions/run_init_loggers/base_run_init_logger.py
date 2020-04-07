from _py_abc import ABCMeta
from abc import abstractmethod

from pypads.functions.loggers.base_logger import DependencyMixin


class RunInitLoggingFunction(DependencyMixin):
    __metaclass__ = ABCMeta
    """
    This class should be used to define new loggers
    """

    def __init__(self, nested=False, **static_parameters):
        self._nested = nested
        self._static_parameters = static_parameters

    def __call__(self, pads, *args, **kwargs):
        from pypads.base import is_nested_run
        if self._nested or not is_nested_run():
            self._call(pads, *args, **{**self._static_parameters, **kwargs})

    @abstractmethod
    def _call(self, pads, *args, **kwargs):
        pass
