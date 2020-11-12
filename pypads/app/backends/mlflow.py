import os
import sys
from abc import ABCMeta
from typing import List, Union
from uuid import uuid4

import mlflow
from mlflow.entities import ViewType
from mlflow.tracking import MlflowClient, artifact_utils
from mlflow.tracking.fluent import SEARCH_MAX_RESULTS_PANDAS
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from pypads import logger
from pypads.app.backends.backend import BackendInterface
from pypads.app.injections.tracked_object import Artifact
from pypads.app.misc.inheritance import SuperStop
from pypads.model.logger_output import FileInfo, MetricMetaModel, ParameterMetaModel, ArtifactMetaModel, TagMetaModel
from pypads.model.metadata import ModelObject
from pypads.model.models import ResultType, BaseStorageModel, to_reference, IdReference, PathReference, \
    ExperimentModel, get_reference, RunModel
from pypads.utils.logging_util import FileFormats, jsonable_encoder, store_tmp_artifact
from pypads.utils.util import string_to_int, get_run_id
from pypads.variables import MONGO_URL, MONGO_USER, MONGO_PW, MONGO_DB, mongo_db


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
        meta.data = path
        for file_info in self.list_files(run_id=get_run_id(), path=os.path.dirname(path)):
            if file_info.path == os.path.basename(path):
                meta.file_size = file_info.file_size
                break
        self.log_json(meta, uuid4())
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

    def log(self, obj: Union[BaseStorageModel]):
        """
        :param obj: Entry object to be logged
        :return:
        """
        rt = obj.storage_type
        if rt == ResultType.metric:
            obj: MetricMetaModel
            stored_meta = self.log_json(obj, obj.uid)
            mlflow.log_metric(obj.name, obj.data)
            return stored_meta

        elif rt == ResultType.parameter:
            obj: ParameterMetaModel
            stored_meta = self.log_json(obj, obj.uid)
            mlflow.log_param(obj.name, obj.data)
            return stored_meta

        elif rt == ResultType.artifact:
            obj: Union[Artifact, ArtifactMetaModel]
            path = self._log_mem_artifact(path=obj.data, artifact=obj.content(), write_format=obj.file_format)
            # Todo maybe don't store filesize because of performance (querying for file after storing takes time)
            for file_info in self.list_files(run_id=get_run_id(), path=os.path.dirname(path)):
                if file_info.path == os.path.basename(path):
                    obj.file_size = file_info.file_size
                    break
            obj.data = path
            stored_meta = self.log_json(obj, obj.uid)
            return stored_meta

        elif rt == ResultType.tag:
            obj: TagMetaModel
            stored_meta = self.log_json(obj, obj.uid)
            mlflow.set_tag(obj.name, obj.data)
            return stored_meta

        else:
            return self.log_json(obj, obj.uid)

    def log_json(self, obj, uid=None):
        """
        Log a metadata object
        :param obj: Object to store as json
        :param uid: uid or path for storage
        :return:
        """
        rt = obj.storage_type
        if rt == ResultType.embedded:
            # Instead of a path an embedded object should return the object itself and not be stored to our backend
            return obj.dict(force=False, by_alias=True)
        if uid is None:
            uid = obj.uid
        return to_reference(
            {**obj.dict(by_alias=True),
             **{"path": self._log_mem_artifact(str(uid),
                                               obj.json(force=False, by_alias=True)
                                               if isinstance(obj, ModelObject) else obj.json(by_alias=True),
                                               write_format=FileFormats.json)}})

    def get(self, uid, storage_type: Union[str, ResultType], experiment_name=None, experiment_id=None, run_id=None,
            search_dict=None):
        """
        Get result entry with given type and uid.
        :param uid:
        :param search_dict:
        :param experiment_id:
        :param experiment_name:
        :param run_id:
        :param storage_type:
        :return:
        """
        reference = IdReference(uid=uid, storage_type=storage_type,
                                experiment=get_reference(ExperimentModel(uid=experiment_id, name=experiment_name)),
                                run=get_reference(RunModel(uid=str(self.run_id))),
                                backend_uri=self.uri)
        json_data = self.get_json(reference)
        if storage_type == ResultType.artifact:
            return Artifact(**dict(json_data))
        else:
            return json_data

    def get_json(self, reference: IdReference):
        """
        Get json stored for a certain run.
        :param reference:
        :return:
        """
        # TODO search by uid instead
        return self.load_artifact_data(run_id=reference.run.uid,
                                       path=reference.path if isinstance(reference, PathReference) else reference.id)

    def get_by_path(self, run_id, path):
        return self.load_artifact_data(run_id=run_id, path=path)


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
        self._mongo_client = MongoClient(os.environ[MONGO_URL], username=os.environ[MONGO_USER],
                                         password=os.environ[MONGO_PW], authSource=os.environ[MONGO_DB])
        self._db = self._mongo_client[os.environ[MONGO_DB]]
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
            if isinstance(entry, BaseStorageModel):
                entry = entry.dict(by_alias=True)
            elif isinstance(entry, ModelObject):
                entry = entry.dict(force=False, by_alias=True)
            else:
                raise ValueError(f"{entry} of wrong type.")
        if "storage_type" not in entry:
            logger.error(
                f"Tried to log an invalid entry. Json logged data has to define a storage_type. For entry {entry}")
            return None
        if entry['storage_type'] == ResultType.embedded:
            # Instead of a path an embedded object should return the object itself and not be stored to our backend
            return entry
        if uid is not None:
            entry["uid"] = uid
        reference = to_reference(entry)
        _id = reference.id
        entry["_id"] = _id
        storage_type = entry["storage_type"].value if isinstance(entry["storage_type"], ResultType) else entry[
            "storage_type"]
        try:
            try:
                self._db[storage_type].insert_one(jsonable_encoder(entry))
            except DuplicateKeyError as e:
                self._db[storage_type].replace_one({"_id": _id}, jsonable_encoder(entry))
        except Exception as e:
            # TODO maybe handle duplicates
            raise e
        return reference

    def get_json(self, reference: IdReference):
        """
        Get json stored for a certain run.
        :return:
        """
        return self._db[reference.storage_type if isinstance(reference.storage_type,
                                                             str) else reference.storage_type.value].find_one(
            {"_id": reference.id})

    def list(self, storage_type: Union[str, ResultType], experiment_name=None, experiment_id=None, run_id=None,
             search_dict=None):
        if search_dict is None:
            search_dict = {}
        if experiment_name:
            search_dict["experiment.name"] = experiment_name
        if experiment_id:
            search_dict["experiment.uid"] = experiment_name
        if run_id:
            search_dict["run.uid"] = run_id
        return self._get_entry_generator(
            self._db[storage_type if isinstance(storage_type, str) else storage_type.value].find(search_dict))

    def get(self, uid, storage_type: Union[str, ResultType], experiment_name=None, experiment_id=None, run_id=None,
            search_dict=None):
        if search_dict is None:
            search_dict = {}
        search_dict["uid"] = uid
        search_dict["storage_type"] = storage_type
        if experiment_name:
            search_dict["experiment.name"] = experiment_name
        if experiment_id:
            search_dict["experiment.uid"] = experiment_name
        if run_id:
            search_dict["run.uid"] = run_id
        if all([a is not None for a in [experiment_id, run_id]]) is not None:
            search_dict["_id"] = IdReference(uid=uid, storage_type=storage_type, experiment_name=experiment_name,
                                             experiment_id=experiment_id, run_id=run_id,
                                             backend_uri=self.uri).id
        return self._db[storage_type if isinstance(storage_type, str) else storage_type.value].find_one(search_dict)


class MongoSupportedLocalMlFlowBackend(MongoSupportMixin, LocalMlFlowBackend):
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
            if get_current_config()[mongo_db]:
                return MongoSupportedLocalMlFlowBackend(uri=uri, pypads=get_current_pads())
            else:
                return LocalMlFlowBackend(uri=uri, pypads=get_current_pads())
        else:
            if get_current_config()[mongo_db]:
                return MongoSupportedRemoteMlFlowBackend(uri=uri, pypads=get_current_pads())
            else:
                return RemoteMlFlowBackend(uri=uri, pypads=get_current_pads())
