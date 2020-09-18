import os
from typing import List, Type

from pydantic import HttpUrl, BaseModel

from pypads import logger
from pypads.app.env import LoggerEnv
from pypads.app.injections.base_logger import LoggerCall, TrackedObject
from pypads.app.injections.run_loggers import RunSetup
from pypads.arguments import ontology_uri
from pypads.model.domain import LibraryModel
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.logging_util import FileFormats


class DependencyTO(TrackedObject):
    """
    Tracking object class for run env info, i.e dependencies.
    """

    class DependencyModel(TrackedObjectModel):
        uri: HttpUrl = f"{ontology_uri}env/Dependencies"

        dependencies: List[LibraryModel] = []
        pip_freeze: str = ...

        class Config:
            orm_mode = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.DependencyModel

    def __init__(self, *args, tracked_by: LoggerCall, **kwargs):
        super().__init__(*args, tracked_by=tracked_by, **kwargs)

    def _add_dependency(self, pip_freeze):
        for item in pip_freeze:
            name, version = item.split('==')
            self.dependencies.append(LibraryModel(name=name, version=version))
        self.pip_freeze = self.store_artifact(self.get_artifact_path("pip_freeze"), "\n".join(pip_freeze),
                                              write_format=FileFormats.text,
                                              description="dependency list from pip freeze")


class DependencyRSF(RunSetup):
    """Store information about dependencies used in the experimental environment."""

    name = "Dependencies Run Setup Logger"
    uri = f"{ontology_uri}dependency-run-logger"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    _dependencies = {"pip"}

    class DependencyRSFOutput(OutputModel):
        uri: HttpUrl = f"{ontology_uri}DependencyRSF-Output"

        dependencies: DependencyTO.get_model_cls() = None

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.DependencyRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        pads = _pypads_env.pypads
        logger.info("Tracking execution to run with id " + pads.api.active_run().info.run_id)
        dependencies = DependencyTO(tracked_by=_logger_call)
        try:
            # Execute pip freeze
            try:
                # noinspection PyProtectedMember,PyPackageRequirements
                from pip._internal.operations import freeze
            except ImportError:  # pip < 10.0
                # noinspection PyUnresolvedReferences,PyPackageRequirements
                from pip.operations import freeze
            dependencies._add_dependency(list(freeze.freeze()))
        except Exception as e:
            _logger_output.set_failure_state(e)
        finally:
            dependencies.store(_logger_output, "dependencies")


class LoguruTO(TrackedObject):
    """
    Tracking object class for run env info, i.e dependencies.
    """

    class LoguruModel(TrackedObjectModel):
        uri: HttpUrl = f"{ontology_uri}env/Logs"

        logs: str = ...

        class Config:
            orm_mode = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.LoguruModel

    def __init__(self, *args, tracked_by: LoggerCall, **kwargs):
        super().__init__(*args, tracked_by=tracked_by, **kwargs)
        self.logs = self.get_artifact_path("logs.log")


class LoguruRSF(RunSetup):
    """Store all logs of the current run into a file."""

    name = "Loguru Run Setup Logger"
    uri = f"{ontology_uri}loguru-run-logger"

    _dependencies = {"loguru"}

    class LoguruRSFOutput(OutputModel):
        uri: HttpUrl = f"{ontology_uri}LoguruRSF-Output"

        logs: LoguruTO.get_model_cls() = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.LoguruRSFOutput

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        pads = _pypads_env.pypads

        from pypads.app.api import PyPadsApi
        _api: PyPadsApi = pads.api

        from pypads.utils.logging_util import get_temp_folder
        folder = get_temp_folder()

        logs = LoguruTO(tracked_by=_logger_call)

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
                pads.api.log_artifact(file, description="Logs of the current run", artifact_path=logs.path)

        logs.store(_logger_output, "logs")
        _api.register_cleanup_fn("logger_" + str(lid), remove_logger)
