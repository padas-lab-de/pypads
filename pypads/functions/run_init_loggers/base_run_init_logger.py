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


class RunInfo(RunInitLoggingFunction):
    def _call(self, pads, *args, **kwargs):
        print("Tracking execution to run with id " + pads.api.active_run().info.run_id)

        # Execute pip freeze
        try:
            from pip._internal.operations import freeze
        except ImportError:  # pip < 10.0
            from pip.operations import freeze
        pads.api.log_mem_artifact("pip_freeze", "\n".join(freeze.freeze()))
