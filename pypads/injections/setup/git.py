from typing import Type

from pydantic import BaseModel

from pypads.app.env import LoggerEnv
from pypads.app.injections.run_loggers import RunSetup
from pypads.app.injections.tracked_object import TrackedObject, LoggerOutput
from pypads.app.misc.managed_git import ManagedGit
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.logging_util import FileFormats


class GitTO(TrackedObject):
    class GitModel(TrackedObjectModel):
        category: str = "SourceCode-Management"
        description = "Information about the git repository in which the experiment is located.."
        source: str = ...
        version: str = ...
        git_log: str = ...  # reference to the log file

        class Config:
            orm_mode = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.GitModel

    def __init__(self, *args, source, parent: LoggerOutput, **kwargs):
        super().__init__(*args, source=source, parent=parent, **kwargs)

    def add_tag(self, *args, **kwargs):
        self.store_tag(*args, **kwargs)

    def store_git_log(self, name, value, format=FileFormats.text):
        self.git_log = self.store_artifact(name, value,
                                           description="Commit logs for the git repository", write_format=format)


class IGitRSF(RunSetup):
    """
    Function tracking the source code via git.
    """
    name = "Generic Git Run Setup Logger"
    category: str = "GitRunLogger"
    _dependencies = {"git"}

    class IGitRSFOutput(OutputModel):
        category: str = "IGitRSF-Output"
        git_info: str = None

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.IGitRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        pads = _pypads_env.pypads
        _pypads_timeout = kwargs.get("_pypads_timeout") if kwargs.get("_pypads_timeout") else 5
        run = pads.api.active_run()
        tags = run.data.tags
        source_name = tags.get("mlflow.source.name", None)
        if "unittest" not in source_name:
            managed_git: ManagedGit = pads.managed_git_factory(source_name)
            if managed_git:
                repo = managed_git.repo
                git_info = GitTO(parent=_logger_output, source=source_name or repo.working_dir,
                                 version=repo.head.commit.hexsha)
                # Disable pager for returns
                repo.git.set_persistent_git_options(no_pager=True)
                try:
                    git_info.add_tag("pypads.git.description", repo.description, description="Repository description")
                    git_info.add_tag("pypads.git.describe", repo.git.describe("--all"), description="")
                    git_info.store_git_log("pypads.git.log", repo.git.log(kill_after_timeout=_pypads_timeout))
                    remotes = repo.remotes
                    remote_out = "No remotes existing"
                    if len(remotes) > 0:
                        remote_out = ""
                        for remote in remotes:
                            remote_out += remote.name + ": " + remote.url + "\n"
                    git_info.add_tag("pypads.git.remotes", remote_out, description="Remotes of the repositories")
                except Exception as e:
                    _logger_output.set_failure_state(e)
                finally:
                    git_info.store(_logger_output, "git_info")
