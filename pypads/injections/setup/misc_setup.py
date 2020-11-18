import os
from typing import List, Type, Union

from pydantic import BaseModel

from pypads import logger
from pypads.app.env import LoggerEnv
from pypads.app.injections.injection import DelayedResultsMixin
from pypads.app.injections.run_loggers import RunSetup
from pypads.app.injections.tracked_object import TrackedObject
from pypads.model.domain import LibraryModel
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.model.models import IdReference
from pypads.utils.logging_util import FileFormats, get_artifact_dir, get_temp_folder


class DependencyTO(TrackedObject):
    """
    Tracking object class for run env info, i.e dependencies.
    """

    class DependencyModel(TrackedObjectModel):
        type: str = "Dependencies"
        description = "A object holding all dependencies found in the current environment."

        dependencies: List[LibraryModel] = []
        pip_freeze: IdReference = ...

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
    type: str = "DependencyRunLogger"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    _dependencies = {"pip"}

    class DependencyRSFOutput(OutputModel):
        type: str = "DependencyRSF-Output"
        dependencies: IdReference = None

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
        type: str = "Log"
        description = "A log file containing the log output of the run."

        path: str = ...

        # TODO add log_level

        class Config:
            orm_mode = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.LogModel

    def __init__(self, *args, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        super().__init__(*args, parent=parent, **kwargs)
        self.path = os.path.join(get_artifact_dir(self), "logs.log")


class LoguruRSF(DelayedResultsMixin, RunSetup):
    """Store all logs of the current run into a file."""

    @staticmethod
    def finalize_output(pads, logger_call, output, *args, **kwargs):
        logs = pads.cache.run_get("loguru_logger")
        lid = pads.cache.run_get("loguru_logger_lid")
        folder = get_temp_folder()
        try:
            from pypads.pads_loguru import logger_manager
            logger_manager.remove(lid)
        except Exception:
            pass

        import glob
        for file in glob.glob(os.path.join(folder, "run_*.log")):
            pads.api.log_artifact(file, description="Logs of the current run", artifact_path=logs.path)

        output.logs = logs.store()

    name = "Loguru Run Setup Logger"
    type: str = "LoguruRunLogger"

    _dependencies = {"loguru"}

    class LoguruRSFOutput(OutputModel):
        type: str = "LoguruRSF-Output"
        logs: IdReference = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.LoguruRSFOutput

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        pads = _pypads_env.pypads

        if not pads.cache.run_exists("loguru_logger"):
            std_out_logger = LogTO(parent=_logger_output)
            pads.cache.run_add("loguru_logger", std_out_logger)

            from pypads.utils.logging_util import get_temp_folder
            folder = get_temp_folder()
            from pypads.pads_loguru import logger_manager
            lid = logger_manager.add(os.path.join(folder, "run_" + pads.api.active_run().info.run_id + ".log"),
                                     rotation="50 MB",
                                     enqueue=True)
            pads.cache.run_add("loguru_logger_lid", lid)
        else:
            logger.warning("LoguruRSF already registered")


class StdOutRSF(DelayedResultsMixin, RunSetup):
    """Store all stdout output of the current run into a file."""

    @staticmethod
    def finalize_output(pads, logger_call, output, *args, **kwargs):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()

        log_to: LogTO = pads.cache.run_get("std_out_logger")
        path = os.path.join(get_temp_folder(), "logfile.log")
        if os.path.isfile(path):
            log_to.path = pads.api.log_artifact(path, description="StdOut log of the current run",
                                                artifact_path=log_to.path)
        output.logs = log_to.store()
        output.store()

        import sys
        if hasattr(sys.stdout, 'terminal'):
            sys.stdout = sys.stdout.terminal

    name = "StdOut Run Setup Logger"
    type: str = "StdOutRunLogger"

    _dependencies = {}

    class StdOutRSFOutput(OutputModel):
        type: str = "StdOutRSF-Output"
        logs: IdReference = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.StdOutRSFOutput

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()

        if not pads.cache.run_exists("std_out_logger"):
            std_out_logger = LogTO(parent=_logger_output, path="logfile.log")
            pads.cache.run_add("std_out_logger", std_out_logger)
        else:
            logger.warning("StdOutRSF already registered")
            return

        import sys

        class Logger(object):
            def __init__(self):
                temp_folder = get_temp_folder()
                if not os.path.isdir(temp_folder):
                    os.mkdir(temp_folder)
                # TODO close file?
                self.log = open(os.path.join(temp_folder, "logfile.log"), "a")

            @property
            def terminal(self):
                return self._terminal

            def write(self, message):
                self.log.write(message)

            def flush(self):
                # this flush method is needed for python 3 compatibility.
                # this handles the flush command by doing nothing.
                # you might want to specify some extra behavior here.
                pass

        stdout_logger = Logger()

        original_function = getattr(sys.stdout, 'write')
        setattr(sys.stdout, 'original_write', original_function)

        def modified_function(message):
            stdout_logger.write(message)
            sys.stdout.original_write(message)

        setattr(sys.stdout, 'write', modified_function)
