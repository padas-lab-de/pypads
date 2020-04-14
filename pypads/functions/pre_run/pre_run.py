import os
from _py_abc import ABCMeta
from abc import abstractmethod

from pypads import logger
from pypads.functions.loggers.mixins import DependencyMixin, OrderMixin, TimedCallableMixin, IntermediateCallableMixin, \
    ConfigurableCallableMixin


class PreRunFunction(IntermediateCallableMixin, TimedCallableMixin, DependencyMixin, OrderMixin,
                     ConfigurableCallableMixin):
    __metaclass__ = ABCMeta
    """
    This class should be used to define new pre run functions
    """

    @abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abstractmethod
    def _call(self, pads, *args, **kwargs):
        pass

    def __real_call__(self, *args, **kwargs):
        from pypads.pypads import get_current_pads
        return self._call(get_current_pads(), *args, **kwargs)


class RunInfo(PreRunFunction):

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
    def _call(self, pads, *args, **kwargs):
        from pypads.base import PypadsApi
        _api: PypadsApi = pads.api

        from pypads.logging_util import get_base_folder
        folder = get_base_folder()

        # TODO loguru has problems with multiprocessing / make rotation configurable etc
        lid = logger.add(os.path.join(folder, "run_" + _api.active_run().info.run_id + ".log"), rotation="50 MB",
                         enqueue=True)

        import glob

        def remove_logger():
            try:
                logger.remove(lid)
            except Exception:
                pass
            for file in glob.glob(os.path.join(folder, "run_*.log")):
                pads.api.log_artifact(file)

        _api.register_post_fn("logger_" + str(lid), remove_logger)
