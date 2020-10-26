import os
from abc import abstractmethod
from typing import List, Union, Iterable, Any, Type

from mlflow.entities import ViewType
from mlflow.tracking.fluent import SEARCH_MAX_RESULTS_PANDAS
from pydantic import BaseModel

from pypads.model.logger_output import FileInfo, ArtifactMetaModel, ParameterMetaModel, MetricMetaModel, TagMetaModel, \
    TrackedObjectModel, OutputModel, ResultHolderModel
from pypads.model.metadata import ModelObject
from pypads.model.models import BaseStorageModel, ResultType, unwrap_typed_id
from pypads.utils.logging_util import get_temp_folder, read_artifact


class BackendInterface:

    def __init__(self, uri, pypads):
        self._uri = uri
        self._pypads = pypads

    @property
    def uri(self):
        return self._uri

    @property
    def pypads(self):
        return self._pypads

    @abstractmethod
    def log_artifact(self, meta, local_path) -> str:
        """
        Logs an artifact from disk.
        :param meta: ArtifactTracking object holding meta information
        :param local_path: Path from which to take the artifact
        :return: Returns a relative path to the artifact including name and file extension.
        """
        raise NotImplementedError("")

    def log(self, obj: BaseStorageModel):
        """
        Log some entry to backend.
        :param obj: Entry object to be logged
        :param payload: Payload if an memory artifact is to be stored.
        :return:
        """
        raise NotImplementedError("")

    @abstractmethod
    def set_experiment_tag(self, experiment_id, key, value):
        raise NotImplementedError("")

    @abstractmethod
    def get_metric_history(self, run_id, key):
        raise NotImplementedError("")

    @abstractmethod
    def list_experiments(self, view_type):
        raise NotImplementedError("")

    @abstractmethod
    def list_run_infos(self, experiment_id, run_view_type=None):
        raise NotImplementedError("")

    @abstractmethod
    def get_run(self, run_id):
        raise NotImplementedError("")

    @abstractmethod
    def get_experiment(self, experiment_id):
        raise NotImplementedError("")

    @abstractmethod
    def get_experiment_by_name(self, name):
        raise NotImplementedError("")

    @abstractmethod
    def delete_experiment(self, experiment_id):
        raise NotImplementedError("")

    @abstractmethod
    def search_runs(self, experiment_ids, filter_string="", run_view_type=ViewType.ACTIVE_ONLY,
                    max_results=SEARCH_MAX_RESULTS_PANDAS, order_by=None):
        raise NotImplementedError("")

    @abstractmethod
    def create_run(self, experiment_id, start_time=None, tags=None):
        raise NotImplementedError("")

    @abstractmethod
    def create_experiment(self, name, artifact_location=None):
        """Create an experiment.

        :param name: The experiment name. Must be unique.
        :param artifact_location: The location to store run artifacts.
                                  If not provided, the server picks an appropriate default.
        :return: Integer ID of the created experiment.
        """
        raise NotImplementedError("")

    @abstractmethod
    def delete_run(self, run_id):
        """
        Deletes a run with the given ID.
        """
        raise NotImplementedError("")

    @abstractmethod
    def download_artifacts(self, run_id, relative_path, dst_path=None):
        """
        Downloads the artifacts at relative_path to given destination folder.
        :param dst_path:
        :param run_id:
        :param relative_path:
        :return:
        """
        raise NotImplementedError("")

    def load_artifact_data(self, run_id, path):
        return read_artifact(self.download_tmp_artifacts(run_id, path))

    def download_tmp_artifacts(self, run_id, relative_path):
        """
        Downloads the artifact at relative_path to a local temporary folder.
        :param run_id:
        :param relative_path:
        :return:
        """
        local_path = get_temp_folder(self.get_run(run_id))
        if not os.path.exists(os.path.dirname(local_path)):
            os.makedirs(os.path.dirname(local_path))
        return self.download_artifacts(run_id=run_id, relative_path=relative_path, dst_path=local_path)

    @abstractmethod
    def list_files(self, run_id, path=None) -> List[FileInfo]:
        """
        This lists all available artifact files.
        :param run_id:
        :param path:
        :return:
        """
        raise NotImplementedError("")

    def list(self, storage_type: Union[str, ResultType], experiment_name=None, experiment_id=None, run_id=None,
             search_dict=None):
        raise NotImplementedError("The used backend doesn't support this form of querying.")

    def get(self, uid, storage_type: Union[str, ResultType], experiment_name=None, experiment_id=None, run_id=None,
            search_dict=None):
        raise NotImplementedError("The used backend doesn't support this form of querying.")

    def get_json(self, reference):
        raise NotImplementedError("The used backend doesn't support this form of querying.")

    def _get_entry_generator(self, out):
        """
        Tries to build a known model from given dict.
        :param out: Return values
        :return:
        """
        if not isinstance(out, Iterable):
            yield self._construct_model(out)
        for entry in out:
            yield self._construct_model(entry)

    @abstractmethod
    def get_artifact_uri(self, artifact_path=None):
        """
        Get the absolute URI of the specified artifact in the currently active run.
        If `path` is not specified, the artifact root URI of the currently active
        run will be returned.

        :param artifact_path: The run-relative artifact path for which to obtain an absolute URI.
                              For example, "path/to/artifact". If unspecified, the artifact root URI
                              for the currently active run will be returned.
        :return: An *absolute* URI referring to the specified artifact or the currently active run's
                 artifact root. For example, if an artifact path is provided and the currently active
                 run uses an S3-backed store, this may be a uri of the form
                 ``s3://<bucket_name>/path/to/artifact/root/path/to/artifact``. If an artifact path
                 is not provided and the currently active run uses an S3-backed store, this may be a
                 URI of the form ``s3://<bucket_name>/path/to/artifact/root``.
        """
        raise NotImplementedError("")

    @staticmethod
    def _construct_model(out: dict):
        if "storage_type" in out:
            result_type = out["storage_type"]
        else:
            return out

        if result_type == ResultType.artifact.value:
            return ArtifactDataLoader(**out)
        elif result_type == ResultType.parameter.value:
            return ParameterMetaModel(**out)
        elif result_type == ResultType.metric.value:
            return MetricMetaModel(**out)
        elif result_type == ResultType.tag.value:
            return TagMetaModel(**out)
        elif result_type == ResultType.tracked_object.value:
            return ExtendedTrackedObjectModel(**out)
        elif result_type == ResultType.output.value:
            return ExtendedOutputModel(**out)
        else:
            return out


class ArtifactDataLoader(ModelObject):

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._content = None

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return ArtifactMetaModel

    def content(self: Union['ArtifactDataLoader', ArtifactMetaModel]):
        if self._content is not None:
            return self._content
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        return pads.backend.load_artifact_data(self.run.uid, self.data)


class LoadedResultHolder(ResultHolderModel):

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._results = {}

    @property
    def artifact_data(self):
        if ResultType.artifact not in self._results:
            from pypads.app.pypads import get_current_pads
            pads = get_current_pads()
            self._results[ResultType.artifact] = [pads.backend.get(**unwrap_typed_id(o)) for o in self.artifacts]
        return self._results[ResultType.artifact]

    @property
    def metric_data(self):
        if ResultType.metric not in self._results:
            from pypads.app.pypads import get_current_pads
            pads = get_current_pads()
            self._results[ResultType.metric] = [pads.backend.get(**unwrap_typed_id(o)) for o in self.metrics]
        return self._results[ResultType.metric]

    @property
    def tag_data(self):
        if ResultType.tag not in self._results:
            from pypads.app.pypads import get_current_pads
            pads = get_current_pads()
            self._results[ResultType.tag] = [pads.backend.get(**unwrap_typed_id(o)) for o in self.tags]
        return self._results[ResultType.tag]

    @property
    def parameter_data(self):
        if ResultType.parameter not in self._results:
            from pypads.app.pypads import get_current_pads
            pads = get_current_pads()
            self._results[ResultType.parameter] = [pads.backend.get(**unwrap_typed_id(o)) for o in self.parameters]
        return self._results[ResultType.parameter]

    @property
    def tracked_object_data(self):
        if ResultType.tracked_object not in self._results:
            from pypads.app.pypads import get_current_pads
            pads = get_current_pads()
            self._results[ResultType.tracked_object] = [pads.backend.get(**unwrap_typed_id(o)) for o in
                                                        self.tracked_objects]
        return self._results[ResultType.tracked_object]

    def _get_kwargs(self):
        """
        Get kwargs for querying the backend
        :return:
        """
        if self.storage_type == ResultType.output:
            return {"output_id": self.uid}
        elif self.storage_type == ResultType.tracked_object:
            return {"tracked_object_id": self.uid}


class ExtendedTrackedObjectModel(LoadedResultHolder, TrackedObjectModel):
    class Config:
        extra = 'allow'


class ExtendedOutputModel(LoadedResultHolder, OutputModel):
    class Config:
        extra = 'allow'
