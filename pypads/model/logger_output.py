import uuid
from dataclasses import dataclass
from typing import Optional, Union, List

from pydantic import BaseModel

from pypads.model.domain import RunObjectModel
from pypads.model.models import IdBasedEntry, ResultType, ProvenanceModel
from pypads.utils.logging_util import FileFormats


class FallibleModel(BaseModel):
    """
    Model holding an attribute to hold a failure message if the logged data was impacted by some form of failure.
    """
    failed: Optional[str] = ...


class ProducedModel(IdBasedEntry):
    """
    Model object used for results produced by a call
    """
    produced_by: Union[uuid.UUID, str] = ...  # id reference to the logger call, this should be the id in a collection
    producer_type: \
        Union[ResultType, str] = ...  # type reference to the logger call, this can be a collection


class ResultHolderModel(ProducedModel):
    """
    This model holds references to artifacts, parameters, metrics and tags as well as other tracked objects defined
    under it.
    """
    artifacts: List[Union[uuid.UUID, str]] = []  # Id references to artifacts produced in scope of the holder
    parameters: List[Union[uuid.UUID, str]] = []  # Id references to parameters produced in scope of the holder
    metrics: List[Union[uuid.UUID, str]] = []  # Id references to metrics produced in scope of the holder
    tags: List[Union[uuid.UUID, str]] = []  # Id references to tags produced in scope of the holder
    tracked_objects: List[
        Union[uuid.UUID, str]] = []  # Id references to other tracked objects produced in scope of the holder


class ResultModel(ProducedModel, RunObjectModel):
    """
    This represents a result being stored in a holder
    """
    part_of: Union[uuid.UUID, str] = ...  # id reference to the result holder holding this result value
    parent_type: Union[ResultType, str] = ...  # type reference to the result holder


class OutputModel(ResultHolderModel, ProvenanceModel, RunObjectModel, FallibleModel):
    """
    This model represents the output of a singular logger. A logger might be able to produce multiple complex outputs.
    """
    category: str = "LoggerOutput"
    additional_data: Optional[dict] = ...
    name: str = "Output"
    storage_type: Union[ResultType, str] = ResultType.output

    class Config:
        orm_mode = True


class MetadataModel(ResultModel):
    """
    Object holding metadata about the logged result
    """
    description: str = ...
    additional_data: \
        Optional[dict] = {}  # Additional data should hold all persistent additional data (Defined by _persistent)


class TrackedObjectModel(MetadataModel, ProvenanceModel, ResultHolderModel):
    """
    This object represents a single concept being part of an output of a logger. Here multiple artifacts can be
    combined to represent a more complex concept.
    """
    category: str = "TrackedObject"
    name: str = "GenericTrackedObject"
    storage_type: Union[ResultType, str] = ResultType.tracked_object

    class Config:
        orm_mode = True


def extract_persistent_data(data):
    if "_persistent" in data:
        return data["_persistent"]
    else:
        return {}


@dataclass  # No validation
class FileInfo:
    is_dir: bool = ...
    path: str = ...
    file_size: int = ...


class MetricMetaModel(MetadataModel):
    """
    Metric Metadata object to be stored in MongoDB.
    """
    name: str = ...
    step: int = ...
    category: str = "MLMetric"
    storage_type: Union[ResultType, str] = ResultType.metric
    data: Union[float, List[float], str] = ...  # float, float history or path to artifact

    class Config:
        orm_mode = True


class ParameterMetaModel(MetadataModel):
    """
    Parameter metadata to be stored in MongoDB as part of an tracking object.
    """
    name: str = ...
    value_format: str = ...
    category: str = "HyperParameter"
    storage_type: Union[ResultType, str] = ResultType.parameter
    data: Optional[str] = ...  # str representation of the parameter or path to artifact

    class Config:
        orm_mode = True


class ArtifactMetaModel(MetadataModel):
    """
    Metadata to be stored in MongoDB as part of an Tracking Object.
    """
    file_format: FileFormats = ...
    category: str = "Artifact"
    storage_type: Union[ResultType, str] = ResultType.artifact
    file_size: int = ...
    data: str = ...  # Path to the artifact

    class Config:
        orm_mode = True


class TagMetaModel(MetadataModel):
    """
    Tag metadata to be stored in MongoDB as part of an Tracking Object.  The tag value is mirrored into mlflow.
    """
    category: str = "MLTag"
    name: str = ...
    value_format: str = ...
    storage_type: Union[ResultType, str] = ResultType.tag
    data: str = ...  # tag value

    class Config:
        orm_mode = True
