import os
import sys
from abc import ABCMeta
from typing import List, Union

import mlflow
from mlflow.entities import ViewType
from mlflow.tracking import MlflowClient, artifact_utils
from mlflow.tracking.fluent import SEARCH_MAX_RESULTS_PANDAS
from pymongo import MongoClient

from pypads import logger
from pypads.app.backends.backend import BackendInterface
from pypads.app.injections.tracked_object import ArtifactTO
from pypads.app.misc.inheritance import SuperStop
from pypads.model.logger_output import FileInfo, MetricMetaModel, ParameterMetaModel, ArtifactMetaModel, TagMetaModel
from pypads.model.models import ResultType, IdBasedEntry
from pypads.utils.logging_util import FileFormats, jsonable_encoder, store_tmp_artifact
from pypads.utils.util import string_to_int, get_run_id


class MLFlowBackend(BackendInterface, metaclass=ABCMeta):
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
        return self.mlf.download_artifacts(run_id, relative_path, dst_path=dst_path)

    def list_files(self, run_id, path=None) -> List[FileInfo]:
        return [FileInfo(is_dir=a.is_dir, path=a.path, file_size=a.file_size) for a in
                self.mlf.list_artifacts(run_id, path=path)]

    def get_artifact_uri(self, artifact_path=""):
        return mlflow.get_artifact_uri(artifact_path=artifact_path)

    def log_artifact(self, meta, local_path):
        path = self._log_artifact(local_path=local_path, artifact_path=meta.data)
        meta.value = path
        self.log_json(meta)
        return path

    def _log_artifact(self, local_path, artifact_path=""):
        mlflow.log_artifact(local_path, artifact_path)
        path = os.path.join(artifact_path if artifact_path else "", local_path.rsplit(os.sep, 1)[1])
        return path

    def _log_mem_artifact(self, path: str, artifact, write_format, preserveFolder=True):
        tmp_path = store_tmp_artifact(path, artifact, write_format=write_format)
        if preserveFolder:
            artifact_path = ""
            splits = path.rsplit(os.sep, 1)
            if len(splits) > 1:
                artifact_path = splits[0]
            return self._log_artifact(tmp_path, artifact_path=artifact_path)
        return self._log_artifact(tmp_path)

    def set_experiment_tag(self, experiment_id, key, value):
        return self.mlf.set_experiment_tag(experiment_id, key, value)

    def log(self, obj: Union[IdBasedEntry]):
        """
        :param obj: Entry object to be logged
        :return:
        """
        rt = obj.storage_type
        if rt == ResultType.metric:
            obj: MetricMetaModel
            stored_meta = self.log_json(obj, obj.typed_id())
            mlflow.log_metric(obj.name, obj.data)
            return stored_meta

        elif rt == ResultType.parameter:
            obj: ParameterMetaModel
            stored_meta = self.log_json(obj, obj.typed_id())
            mlflow.log_param(obj.name, obj.data)
            return stored_meta

        elif rt == ResultType.artifact:
            obj: ArtifactMetaModel
            path = self._log_mem_artifact(path=obj.data, artifact=obj.content(), write_format=obj.file_format)
            # Todo maybe don't store filesize because of performance (querying for file after storing takes time)
            for file_info in self.list_files(run_id=get_run_id(), path=os.path.dirname(path)):
                if file_info.path == os.path.basename(path):
                    obj.file_size = file_info.file_size
                    break
            obj.data = path
            stored_meta = self.log_json(obj, obj.typed_id())
            return stored_meta

        elif rt == ResultType.tag:
            obj: TagMetaModel
            stored_meta = self.log_json(obj, obj.typed_id())
            mlflow.set_tag(obj.name, obj.data)
            return stored_meta

        else:
            return self.log_json(obj, obj.typed_id())

    def log_json(self, obj, uid=None):
        """
        Log a metadata object
        :param obj: Object to store as json
        :param uid: uid or path for storage
        :return:
        """
        if uid is None:
            uid = obj.uid
        return self._log_mem_artifact(uid, obj.json(by_alias=True),
                                      write_format=FileFormats.json)

    def get(self, run_id, uid, storage_type: Union[ResultType, str]):
        json_data = self.get_json(run_id=run_id, uid=uid, storage_type=storage_type)
        if storage_type == ResultType.artifact:
            return ArtifactTO(**dict(json_data))
        else:
            return json_data

    def get_json(self, run_id, uid, storage_type=None):
        """
        Get json stored for a certain run.
        :param storage_type: Storage type to look for
        :param run_id: Id of the run
        :param uid: uid - for local storage this is the relative path
        :return:
        """
        return self.load_artifact_data(run_id=run_id, path=uid)


class LocalMlFlowBackend(MLFlowBackend):

    def list(self, storage_type: Union[str, ResultType], experiment_name=None, experiment_id=None, run_id=None,
             search_dict=None):
        raise NotImplementedError(
            "List is currently not implemented for local stores. Use a MongoDB supported store for this feature.")

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
        local_location = os.path.join(dst_path, relative_path)
        if os.path.exists(local_location):  # TODO check file digest or something similar??
            logger.debug(
                f"Skipped downloading file because a file f{local_location} with the same name already exists.")
            return local_location

        return artifact_utils.get_artifact_uri(run_id=run_id, artifact_path=relative_path)

    def manage_results(self, result_path):
        """
        If we should push results for the user use a managed git.
        :param result_path: Path where the result git should be.
        :return:
        """
        self._managed_result_git = self.pypads.managed_git_factory(result_path, source=False)

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

    def list(self, storage_type: Union[str, ResultType], experiment_name=None, experiment_id=None, run_id=None,
             search_dict=None):
        raise NotImplementedError(
            "List is currently not implemented for mlflow stores. Use a MongoDB supported store for this feature.")

    def __init__(self, uri, pypads):
        """
        Remote version of an mlflow backend.
        :param uri:
        :param pypads:
        """
        super().__init__(uri, pypads)


class MongoSupportMixin(BackendInterface, SuperStop, metaclass=ABCMeta):
    def __init__(self, *args, **kwargs):
        self._mongo_client = MongoClient(os.environ['MONGO_URL'], username=os.environ['MONGO_USER'],
                                         password=os.environ['MONGO_PW'], authSource=os.environ['MONGO_DB'])
        self._db = self._mongo_client[os.environ['MONGO_DB']]
        super().__init__(*args, **kwargs)

    @staticmethod
    def _path_to_id(path, run_id=None):
        from pypads.app.pypads import get_current_pads
        if run_id is None:
            run = get_current_pads().api.active_run()
            run_id = run.info.run_id
            experiment_name = mlflow.get_experiment(mlflow.active_run().info.experiment_id).name
        else:
            experiment_name = mlflow.get_experiment(mlflow.active_run().info.experiment_id).name
        return os.path.sep.join([experiment_name, run_id, path])

    def log_json(self, entry, uid=None):
        if not isinstance(entry, dict):
            entry = entry.dict(by_alias=True)
        if uid is None:
            uid = entry.uid
        entry["_id"] = uid
        if "storage_type" not in entry:
            logger.error(
                f"Tried to log an invalid entry. Json logged data has to define a storage_type. For entry {entry}")
            return None
        try:
            self._db[entry["storage_type"].value if isinstance(entry["storage_type"], ResultType) else entry[
                "storage_type"]].insert_one(jsonable_encoder(entry))
        except Exception as e:
            logger.error(e)
        return entry["_id"]

    def get_json(self, run_id, uid, storage_type: Union[str, ResultType] = None):
        """
        Get json stored for a certain run.
        :param storage_type: Storage type to look for
        :param run_id: Id of the run
        :param uid: uid - for local storage this is the relative path
        :return:
        """
        return self._db[storage_type if isinstance(storage_type, str) else storage_type.value].find_one(
            {"_id": uid, "run_id": run_id})

    def list(self, storage_type: Union[str, ResultType], experiment_name=None, experiment_id=None, run_id=None,
             search_dict=None):
        if search_dict is None:
            search_dict = {}
        if experiment_name:
            search_dict["experiment_name"] = experiment_name
        if experiment_id:
            search_dict["experiment_id"] = experiment_id
        if run_id:
            search_dict["run_id"] = run_id
        return self._db[storage_type if isinstance(storage_type, str) else storage_type.value].find(search_dict)


class MongoSupportedLocalMlFlowBackend(MongoSupportMixin, RemoteMlFlowBackend):
    def __init__(self, uri, pypads):
        super().__init__(uri, pypads)


class MongoSupportedRemoteMlFlowBackend(MongoSupportMixin, RemoteMlFlowBackend):
    def __init__(self, uri, pypads):
        super().__init__(uri, pypads)


# TODO add elastic search?


class MLFlowBackendFactory:

    @staticmethod
    def make(uri) -> MLFlowBackend:
        from pypads.app.pypads import get_current_pads, get_current_config
        if uri.startswith("git://") or uri.startswith("/"):
            if get_current_config()["mongo_db"]:
                return MongoSupportedLocalMlFlowBackend(uri=uri, pypads=get_current_pads())
            else:
                return LocalMlFlowBackend(uri=uri, pypads=get_current_pads())
        else:
            if get_current_config()["mongo_db"]:
                return MongoSupportedRemoteMlFlowBackend(uri=uri, pypads=get_current_pads())
            else:
                return RemoteMlFlowBackend(uri=uri, pypads=get_current_pads())
