import os

from app.env import LoggingEnv
from pydantic import HttpUrl, BaseModel
from typing import List, Type

from pypads import logger
from pypads.app.injections.base_logger import LoggerCall, TrackedObject
from pypads.app.injections.run_loggers import RunSetupFunction
from pypads.model.models import TrackingObjectModel, LibraryModel


class DependencyTO(TrackedObject):
    """
    Tracking object class for run env info, i.e dependencies.
    """
    class DependencyModel(TrackingObjectModel):
        uri: HttpUrl = "https://www.padre-lab.eu/onto/env/Dependencies"
        dependencies: List[LibraryModel] = []

    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.DependencyModel

    def __init__(self, *args, call: LoggerCall, **kwargs):
        super().__init__(*args, original_call=call, **kwargs)

    def _add_dependency(self, name):
        pass


class DependencyRSF(RunSetupFunction):
    """Store information about dependencies used in the experimental environment."""

    name = "Dependencies Run Setup Logger"
    uri = "https://www.padre-lab.eu/onto/dependency-run-logger"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    _dependencies = {"pip"}

    def _call(self, *args, _pypads_env: LoggingEnv, **kwargs):
        pads = _pypads_env.pypads
        logger.info("Tracking execution to run with id " + pads.api.active_run().info.run_id)

        # Execute pip freeze
        try:
            # noinspection PyProtectedMember,PyPackageRequirements
            from pip._internal.operations import freeze
        except ImportError:  # pip < 10.0
            # noinspection PyUnresolvedReferences,PyPackageRequirements
            from pip.operations import freeze
        pads.api.log_mem_artifact("pip_freeze", "\n".join(freeze.freeze()))


class RunLogger(RunSetupFunction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _call(self, *args, _pypads_env: LoggingEnv, **kwargs):
        pads = _pypads_env.pypads

        from pypads.app.api import PyPadsApi
        _api: PyPadsApi = pads.api

        from pypads.utils.logging_util import get_temp_folder
        folder = get_temp_folder()

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

        _api.register_teardown_fn("logger_" + str(lid), remove_logger)
