import os
import sys
from typing import List

import mlflow
from mlflow.entities import ViewType
from mlflow.tracking import MlflowClient, artifact_utils
from mlflow.tracking.fluent import SEARCH_MAX_RESULTS_PANDAS

from pypads import logger
from pypads.app.backends.backend import BackendInterface
from pypads.model.storage import FileInfo
from pypads.utils.logging_util import store_tmp_artifact
from pypads.utils.util import string_to_int


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

    @property
    def mlf(self) -> MlflowClient:
        return MlflowClient(self.uri)

    def list_run_infos(self, experiment_id, run_view_type=ViewType.ALL):
        return self.mlf.list_run_infos(experiment_id=experiment_id, run_view_type=run_view_type)

    def get_metric_history(self, run_id, key):
        return self.mlf.get_metric_history(run_id, key)

    def list_experiments(self, view_type=ViewType.ALL):
        return self.mlf.list_experiments(view_type=view_type)

    def get_run(self, run_id):
        return mlflow.get_run(run_id)

    def get_experiment(self, experiment_id):
        return mlflow.get_experiment(experiment_id)

    def get_experiment_by_name(self, name):
        return mlflow.get_experiment_by_name(name)

    def delete_experiment(self, experiment_id):
        return mlflow.delete_experiment(experiment_id)

    def search_runs(self, experiment_ids, filter_string="", run_view_type=ViewType.ACTIVE_ONLY,
                    max_results=SEARCH_MAX_RESULTS_PANDAS, order_by=None):
        return mlflow.search_runs(experiment_ids, filter_string=filter_string, run_view_type=run_view_type,
                                  max_results=max_results, order_by=order_by)

    def create_run(self, experiment_id, start_time=None, tags=None):
        return self.mlf.create_run(experiment_id, start_time=start_time, tags=tags)

    def create_experiment(self, name, artifact_location=None):
        return self.mlf.create_experiment(name, artifact_location=artifact_location)

    def delete_run(self, run_id):
        return mlflow.delete_run(run_id)

    def download_artifacts(self, run_id, relative_path, dst_path=None):
        return self.mlf.download_artifacts(run_id, relative_path, dst_path=None)

    def list_files(self, run_id, path=None) -> List[FileInfo]:
        return [FileInfo(is_dir=a.is_dir, path=a.path, file_size=a.file_size) for a in
                self.mlf.list_artifacts(run_id, path=path)]

    def get_artifact_uri(self, artifact_path=""):
        return mlflow.get_artifact_uri(artifact_path=artifact_path)

    def log_artifact(self, local_path, artifact_path=""):
        mlflow.log_artifact(local_path, artifact_path)
        return os.path.join(artifact_path, local_path.rsplit(os.sep, 1)[1])

    def log_mem_artifact(self, path: str, artifact, write_format, preserveFolder=True):
        tmp_path = store_tmp_artifact(path, artifact, write_format=write_format)
        if preserveFolder:
            artifact_path = ""
            splits = path.rsplit(os.sep, 1)
            if len(splits) > 1:
                artifact_path = splits[0]
            return self.log_artifact(tmp_path, artifact_path=artifact_path)
        return self.log_artifact(tmp_path)

    def log_metric(self, name, metric, step):
        return mlflow.log_metric(name, metric, step)

    def log_parameter(self, name, parameter):
        return mlflow.log_param(name, parameter)

    def set_tag(self, key, value):
        return mlflow.set_tag(key, value)

    def set_experiment_tag(self, experiment_id, key, value):
        return self.mlf.set_experiment_tag(experiment_id, key, value)


class LocalMlFlowBackend(MLFlowBackend):

    def __init__(self, uri, pypads):
        """
        Local version of a mlflow backend. This can push its results to a git if needed.
        :param uri:
        :param pypads:
        """
        manage_results = uri.startswith("git://")

        self._managed_result_git = None

        # If the results should be git managed
        if manage_results:
            result_path = uri[5:]
            uri = os.path.join(uri[5:], "r_" + str(string_to_int(uri)), "experiments")
            super().__init__(uri, pypads)
            self.manage_results(result_path)
            pypads.cache.add('uri', uri)
        else:
            super().__init__(uri, pypads)

    @property
    def managed_result_git(self):
        return self._managed_result_git

    def download_tmp_artifacts(self, run_id, relative_path):
        return artifact_utils.get_artifact_uri(run_id=run_id, artifact_path=relative_path)

    def download_artifacts(self, run_id, relative_path, dst_path=None):
        return artifact_utils.get_artifact_uri(run_id=run_id, artifact_path=relative_path)

    def manage_results(self, result_path):
        """
        If we should push results for the user use a managed git.
        :param result_path: Path where the result git should be.
        :return:
        """
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

        self.pypads.api.register_teardown_utility("commit", commit,
                                                  error_message="A problem executing the result management function was detected."
                                                                " Check if you have to commit / push results manually."
                                                                " Following exception caused the problem: {0}",
                                                  order=sys.maxsize - 1)

    def add_result_remote(self, remote, uri):
        """
        Add a remote to track the results.
        :param remote: Remote name to be added
        :param uri: Remote address to be added
        :return:
        """
        if self.managed_result_git is None:
            raise Exception("Can only add remotes to the result directory if it is managed by pypads git.")
        try:
            self.managed_result_git.remote = remote
            self.managed_result_git.remote_uri = uri
            self.managed_result_git.repo.create_remote(remote, uri)
        except Exception as e:
            logger.warning("Failed to add remote due to exception: " + str(e))


class RemoteMlFlowBackend(MLFlowBackend):

    def __init__(self, uri, pypads):
        """
        Remote version of an mlflow backend.
        :param uri:
        :param pypads:
        """
        super().__init__(uri, pypads)


class MLFlowBackendFactory:

    @staticmethod
    def make(uri) -> MLFlowBackend:
        from pypads.app.pypads import get_current_pads
        if uri.startswith("git://") or uri.startswith("/"):
            return LocalMlFlowBackend(uri=uri, pypads=get_current_pads())
        else:
            return RemoteMlFlowBackend(uri=uri, pypads=get_current_pads())
