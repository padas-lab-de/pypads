import os
import sys
from abc import abstractmethod

import mlflow
from mlflow.tracking import MlflowClient

from pypads import logger
from pypads.app.injections.base_logger import TrackedObject, LoggerOutput
from pypads.model.models import ArtifactMetaModel, MetricMetaModel, ParameterMetaModel, TagMetaModel
from pypads.utils.logging_util import try_write_artifact, WriteFormats
from pypads.utils.util import string_to_int


class BackendInterface:

    def __init__(self, uri, pypads):
        self._uri = uri
        self._pypads = pypads
        self._managed_result_git = None

        manage_results = self._uri.startswith("git://")

        # If the results should be git managed
        if manage_results:
            result_path = self._uri[5:]
            self._uri = os.path.join(self._uri[5:], "r_" + str(string_to_int(uri)), "experiments")
            self.manage_results(result_path)
            pypads.cache.add('uri', self._uri)

    @abstractmethod
    def manage_results(self, result_path):
        """
        If we should push results for the user use a managed git.
        :param result_path: Path where the result git should be.
        :return:
        """
        raise NotImplementedError("")

    @abstractmethod
    def add_result_remote(self, remote, uri):
        """
        Add a remote to track the results.
        :param remote: Remote name to be added
        :param uri: Remote address to be added
        :return:
        """
        raise NotImplementedError("")

    @property
    def uri(self):
        return self._uri

    @property
    def pypads(self):
        return self._pypads

    @property
    def managed_result_git(self):
        return self._managed_result_git

    @abstractmethod
    def store_tracked_object(self, to):
        raise NotImplementedError("")

    @abstractmethod
    def store_logger_output(self, lo):
        raise NotImplementedError("")

    @abstractmethod
    def load_tracked_object(self, path):
        raise NotImplementedError("")

    @abstractmethod
    def log_artifact(self, artifact, meta: ArtifactMetaModel):
        raise NotImplementedError("")

    @abstractmethod
    def log_metric(self, metric, meta: MetricMetaModel):
        raise NotImplementedError("")

    @abstractmethod
    def log_parameter(self, parameter, meta: ParameterMetaModel):
        raise NotImplementedError("")

    @abstractmethod
    def set_tag(self, tag, meta: TagMetaModel):
        raise NotImplementedError("")


class MLFlowBackend(BackendInterface):
    """
    Backend pushing data to mlflow
    """

    def __init__(self, uri, pypads):
        """
        :param uri: Location in which we want to write results.
        :param pypads: Owning pypads instance
        :return:
        """
        super().__init__(uri, pypads)
        # Set the tracking uri
        mlflow.set_tracking_uri(self._uri)

    def manage_results(self, result_path):
        self._managed_result_git = self.pypads.managed_git_factory(result_path)

        def commit(pads, *args, **kwargs):
            message = "Added results for run " + pads.api.active_run().info.run_id
            pads.managed_result_git.commit_changes(message=message)

            repo = pads.managed_result_git.repo
            remotes = repo.remotes

            if not remotes:
                logger.warning(
                    "Your results don't have any remote repository set. Set a remote repository for"
                    "to enable automatic pushing.")
            else:
                for remote in remotes:
                    name, url = remote.name, list(remote.urls)[0]
                    try:
                        # check if remote repo is bare and if it is initialize it with a temporary local repo
                        pads.managed_result_git.is_remote_empty(remote=name,
                                                                remote_url=url,
                                                                init=True)
                        # stash current state
                        repo.git.stash('push', '--include-untracked')
                        # Force pull
                        repo.git.pull(name, 'master', '--allow-unrelated-histories')
                        # Push merged changes
                        repo.git.push(name, 'master')
                        logger.info("Pushed your results automatically to " + name + " @:" + url)
                        # pop the stash
                        repo.git.stash('pop')
                    except Exception as e:
                        logger.error("pushing logs to remote failed due to this error '{}'".format(str(e)))

        self.pypads.api.register_teardown_fn("commit", commit, nested=False, intermediate=False,
                                             error_message="A problem executing the result management function was detected."
                                                           " Check if you have to commit / push results manually."
                                                           " Following exception caused the problem: {0}",
                                             order=sys.maxsize - 1)

    def add_result_remote(self, remote, uri):
        if self.managed_result_git is None:
            raise Exception("Can only add remotes to the result directory if it is managed by pypads git.")
        try:
            self.managed_result_git.remote = remote
            self.managed_result_git.remote_uri = uri
            self.managed_result_git.repo.create_remote(remote, uri)
        except Exception as e:
            logger.warning("Failed to add remote due to exception: " + str(e))

    @property
    def mlf(self) -> MlflowClient:
        return MlflowClient(self.uri).list_experiments()

    def store_tracked_object(self, to: TrackedObject, path=""):
        path += "{}#{}".format(to.__class__.__name__, id(to))
        try_write_artifact(path, to.json(), write_format=WriteFormats.json)
        return path

    def store_logger_output(self, lo: LoggerOutput, path=""):
        path += "{}/{}".format("Output", id(lo))
        try_write_artifact(path, lo.json(), write_format=WriteFormats.json)
        return path

    def log_artifact(self, artifact, meta: ArtifactMetaModel):
        try_write_artifact(meta.path, artifact, write_format=meta.format)

    def log_metric(self, metric, meta: MetricMetaModel):
        mlflow.log_metric(meta.name, metric)

    def log_parameter(self, parameter, meta: ParameterMetaModel):
        mlflow.log_param(meta.name, parameter)

    def set_tag(self, tag, meta: TagMetaModel):
        mlflow.set_tag(meta.name, tag)
