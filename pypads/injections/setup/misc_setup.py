import os
import uuid
from typing import List, Type, Union

from pydantic import BaseModel

from pypads import logger
from pypads.app.env import LoggerEnv
from pypads.app.injections.run_loggers import RunSetup
from pypads.app.injections.tracked_object import TrackedObject
from pypads.model.domain import LibraryModel
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.logging_util import FileFormats, get_artifact_dir


class DependencyTO(TrackedObject):
    """
    Tracking object class for run env info, i.e dependencies.
    """

    class DependencyModel(TrackedObjectModel):
        category: str = "Dependencies"
        description = "A object holding all dependencies found in the current environment."

        dependencies: List[LibraryModel] = []
        pip_freeze: Union[uuid.UUID, str] = ...

        class Config:
            orm_mode = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.DependencyModel

    def __init__(self, *args, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        super().__init__(*args, parent=parent, **kwargs)

    def add_dependency(self: Union['DependencyTO', DependencyModel], pip_freeze):
        for item in pip_freeze:
            splits = item.split('==')
            if len(splits) == 2:
                name, version = splits
                self.dependencies.append(LibraryModel(name=name, version=version))
        self.pip_freeze = self.store_mem_artifact("pip_freeze", "\n".join(pip_freeze),
                                                  write_format=FileFormats.text,
                                                  description="dependency list from pip freeze")

    # def get_artifact_path(self, name):
    #     return os.path.join(str(id(self)), "Env", name)


class DependencyRSF(RunSetup):
    """Store information about dependencies used in the experimental environment."""

    name = "Dependencies Run Setup Logger"
    category: str = "DependencyRunLogger"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    _dependencies = {"pip"}

    class DependencyRSFOutput(OutputModel):
        category: str = "DependencyRSF-Output"
        dependencies: Union[uuid.UUID, str] = None

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.DependencyRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        pads = _pypads_env.pypads
        logger.info("Tracking execution to run with id " + pads.api.active_run().info.run_id)
        dependencies = DependencyTO(parent=_logger_output)
        try:
            # Execute pip freeze
            try:
                # noinspection PyProtectedMember,PyPackageRequirements
                from pip._internal.operations import freeze
            except ImportError:  # pip < 10.0
                # noinspection PyUnresolvedReferences,PyPackageRequirements
                from pip.operations import freeze
            dependencies.add_dependency(list(freeze.freeze()))
        except Exception as e:
            _logger_output.set_failure_state(e)
        finally:
            _logger_output.dependencies = dependencies.store()


class LogTO(TrackedObject):
    """
    Tracking object class for run env info, i.e dependencies.
    """

    class LogModel(TrackedObjectModel):
        category: str = "Log"
        description = "A log file containing the log output of the run."

        path: Union[uuid.UUID, str] = ...

        # TODO add log_level

        class Config:
            orm_mode = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.LogModel

    def __init__(self, *args, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        super().__init__(*args, parent=parent, **kwargs)
        self.path = os.path.join(get_artifact_dir(self), "logs.log")


class LoguruRSF(RunSetup):
    """Store all logs of the current run into a file."""

    name = "Loguru Run Setup Logger"
    category: str = "LoguruRunLogger"

    _dependencies = {"loguru"}

    class LoguruRSFOutput(OutputModel):
        category: str = "LoguruRSF-Output"
        logs: Union[uuid.UUID, str] = ...

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

        logs = LogTO(parent=_logger_output)

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

        _logger_output.logs = logs.store()
        _api.register_teardown_utility("logger_" + str(lid), remove_logger)
