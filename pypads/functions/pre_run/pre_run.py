import os
from _py_abc import ABCMeta
from abc import abstractmethod

from pypads import logger
from pypads.functions.loggers.base_logger import FunctionHolder
from pypads.functions.loggers.mixins import DependencyMixin, OrderMixin, TimedCallableMixin, IntermediateCallableMixin, \
    ConfigurableCallableMixin, DefensiveCallableMixin


class PreRunFunction(DefensiveCallableMixin, IntermediateCallableMixin, FunctionHolder, TimedCallableMixin, DependencyMixin, OrderMixin,
                     ConfigurableCallableMixin):
    """
    This class should be used to define new pre run functions
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, *args, fn=None, **kwargs):
        super().__init__(*args, fn=fn, **kwargs)
        if self._fn is None:
            self._fn = self._call

    @abstractmethod
    def _call(self, pads, *args, **kwargs):
        """
        Function where to add you custom code to execute before starting the run.

        :param pads: the current instance of PyPads.
        """
        return NotImplementedError()

    def __real_call__(self, *args, **kwargs):
        from pypads.pypads import get_current_pads
        return super().__real_call__(get_current_pads(), *args, **kwargs)


class RunInfo(PreRunFunction):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def _needed_packages():
        return ["pip"]

    def _call(self, pads, *args, **kwargs):
        logger.info("Tracking execution to run with id " + pads.api.active_run().info.run_id)

        # Execute pip freeze
        try:
            # noinspection PyProtectedMember,PyPackageRequirements
            from pip._internal.operations import freeze
        except ImportError:  # pip < 10.0
            # noinspection PyUnresolvedReferences,PyPackageRequirements
            from pip.operations import freeze
        pads.api.log_mem_artifact("pip_freeze", "\n".join(freeze.freeze()))


class RunLogger(PreRunFunction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _call(self, pads, *args, **kwargs):
        from pypads.base import PypadsApi
        _api: PypadsApi = pads.api

        from pypads.logging_util import get_base_folder
        folder = get_base_folder()

        # TODO loguru has problems with multiprocessing / make rotation configurable etc
        from pypads.pads_loguru import logger_manager
        lid = logger_manager.add(os.path.join(folder, "run_" + _api.active_run().info.run_id + ".log"),
                                 rotation="50 MB",
                                 enqueue=True)

        import glob

        def remove_logger(pads, *args, **kwargs):
            try:
                from pypads.pads_loguru import logger_manager
                logger_manager.remove(lid)
            except Exception:
                pass
            for file in glob.glob(os.path.join(folder, "run_*.log")):
                pads.api.log_artifact(file)

        _api.register_post_fn("logger_" + str(lid), remove_logger)
