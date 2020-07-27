import os
from typing import List, Type

from pydantic import HttpUrl, BaseModel

from app.env import LoggerEnv
from pypads import logger
from pypads.app.injections.base_logger import LoggerCall, TrackedObject
from pypads.app.injections.run_loggers import RunSetup
from pypads.model.models import TrackedObjectModel, LibraryModel, OutputModel, ArtifactMetaModel
from pypads.utils.logging_util import WriteFormats


class DependencyTO(TrackedObject):
    """
    Tracking object class for run env info, i.e dependencies.
    """

    class DependencyModel(TrackedObjectModel):
        uri: HttpUrl = "https://www.padre-lab.eu/onto/env/Dependencies"

        dependencies: List[LibraryModel] = []
        content_format: WriteFormats = WriteFormats.text

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
        path = os.path.join(self._base_path(), self._get_artifact_path("pip_freeze"))
        self._store_artifact("\n".join(pip_freeze),
                             ArtifactMetaModel(path=path, description="dependency list from pip freeze",
                                               format=WriteFormats.text))

    def _get_artifact_path(self, name):
        return os.path.join(str(id(self)), "Env", name)


class DependencyRSF(RunSetup):
    """Store information about dependencies used in the experimental environment."""

    name = "Dependencies Run Setup Logger"
    uri = "https://www.padre-lab.eu/onto/dependency-run-logger"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    _dependencies = {"pip"}

    class DependencyRSFOutput(OutputModel):
        uri: HttpUrl = "https://www.padre-lab.eu/onto/DependencyRSF-Output"

        dependencies: DependencyTO.get_model_cls() = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.DependencyRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        pads = _pypads_env.pypads
        logger.info("Tracking execution to run with id " + pads.api.active_run().info.run_id)
        dependencies = DependencyTO(tracked_by=_logger_call)
        # Execute pip freeze
        try:
            # noinspection PyProtectedMember,PyPackageRequirements
            from pip._internal.operations import freeze
        except ImportError:  # pip < 10.0
            # noinspection PyUnresolvedReferences,PyPackageRequirements
            from pip.operations import freeze
        dependencies._add_dependency(freeze.freeze())
        dependencies.store(_logger_output, "dependencies")


class LoguruRSF(RunSetup):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _call(self, *args, _pypads_env: LoggerEnv, **kwargs):
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
