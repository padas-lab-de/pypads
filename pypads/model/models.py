import os
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl, root_validator

from pypads.arguments import ontology_uri
from pypads.utils.logging_util import FileFormats
from pypads.utils.util import get_experiment_id, get_run_id, persistent_hash

DEFAULT_CONTEXT = {
    "uri": "@id",
    "is_a": "@type",
    "experiment_id": {
        "@id": f"{ontology_uri}contained_in",
        "@type": f"{ontology_uri}Experiment"
    },
    "run_id": {
        "@id": f"{ontology_uri}contained_in",
        "@type": f"{ontology_uri}Run"
    },
    "created_at": {
        "@id": f"{ontology_uri}created_at",
        "@type": "http://www.w3.org/2001/XMLSchema#dateTime"
    },
    "name": {
        "@id": f"{ontology_uri}label",
        "@type": "http://www.w3.org/2001/XMLSchema#string"
    },
    "context": {
        "@id": f"{ontology_uri}relates_to",
        "@type": f"{ontology_uri}Context"
    },
    "reference": {
        "@id": f"{ontology_uri}represents",
        "@type": "http://www.w3.org/2001/XMLSchema#string"
    },
    "tracked_by": {
        "@id": f"{ontology_uri}tracked_by",
        "@type": f"{ontology_uri}LoggerCall"
    },
    "failed": {
        "@id": f"{ontology_uri}failure",
        "@type": "http://www.w3.org/2001/XMLSchema#boolean"
    }
}
default_ctx_path = None


def get_default_ctx_path():
    """
    Function to persist the default context and get it's location.
    :return:
    """
    from pypads.app.pypads import get_current_pads
    pads = get_current_pads()

    global default_ctx_path
    if not default_ctx_path:
        obj = pads.schema_repository.get_object(uid=persistent_hash(str(DEFAULT_CONTEXT)))
        default_ctx_path = obj.get_artifact_path(obj.log_mem_artifact("pypads_context_default", DEFAULT_CONTEXT,
                                                                      write_format=FileFormats.json))
        obj.set_tag("pypads.schema_name", "pypads_context_default")
    return os.path.join(pads.uri, default_ctx_path + ".json")


class OntologyEntry(BaseModel):
    """
    Object representing an (potential) entry in a knowledge base
    """
    uri: HttpUrl = ...
    context: Union[List[str], str] = Field(alias='@context', default=None)

    @root_validator
    def set_default_context(cls, values):
        if values['context'] is None:
            values['context'] = get_default_ctx_path()
        else:
            if isinstance(values['context'], List):
                values['context'].append(get_default_ctx_path())
            else:
                values['context'] = [get_default_ctx_path(), values['context']]
        return values


class LibraryModel(BaseModel):
    """
    Representation of a package or library
    """
    name: str = ...
    version: str = ...
    extracted: bool = False


class LibSelectorModel(BaseModel):
    """
    Representation of a selector for a package
    """
    name: str = ...  # Name of the package. Either a direct string or a regex.
    constraint: str  # Constraint for the version number
    regex: bool = False  # Flag if the name of the selector is to be considered as a regex
    specificity: int  # How specific the selector is ( important for a css like mapping of multiple selectors)

    def __hash__(self):
        return hash((self.name, self.constraint, self.specificity))

    class Config:
        orm_mode = True


class ExperimentModel(OntologyEntry):  # TODO
    name: str = ...


class RunModel(OntologyEntry):  # TODO
    id: str = ...
    name: str = ...


class RunObjectModel(OntologyEntry):
    """
    Base object for tracked objects that manage metadata. A MetadataEntity manages and id and a dict of metadata.
    The metadata should contain all necessary non-binary data to describe an entity.
    """
    experiment_id: Optional[str] = Field(default_factory=get_experiment_id)
    run_id: Optional[str] = Field(default_factory=get_run_id)
    uid: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: float = Field(default_factory=time.time)
    is_a: HttpUrl = ...
    uri: HttpUrl = None

    @root_validator
    def set_default_uri(cls, values):
        if values['uri'] is None:
            values['uri'] = f"{values['is_a']}#{values['uid']}"
        return values

    def store(self):
        """
        Function to store the object as json into an artifact
        :return:
        """
        from pypads.app.pypads import get_current_pads
        get_current_pads().api.log_mem_artifact("{}#{}".format(self.__class__.__name__, self.uid),
                                                self.json(by_alias=True),
                                                write_format=FileFormats.json,
                                                path=os.path.join(self.__class__.__name__, str(self.uid)))


class LoggerModel(RunObjectModel):
    """
    A reference object for a logger.
    """
    name: str = "GenericTrackingFunction"
    uid: uuid.UUID = Field(default_factory=uuid.uuid4)
    is_a: HttpUrl = f"{ontology_uri}logger"
    dependencies: List[LibSelectorModel] = {}
    supported_libraries: List[LibSelectorModel] = ...
    allow_nested: bool = True
    allow_intermediate: bool = True

    class Config:
        orm_mode = True


class RunLoggerModel(LoggerModel):
    """
    Tracking function being executed on run teardown or setup
    """
    name: str = "GenericRunLogger"
    is_a: HttpUrl = f"{ontology_uri}run-logger"

    class Config:
        orm_mode = True


class InjectionLoggerModel(LoggerModel):
    """
    Tracking function being exectured on injection hook execution
    """
    name: str = "GenericInjectionLogger"
    is_a: HttpUrl = f"{ontology_uri}injection-logger"

    class Config:
        orm_mode = True


class ContextModel(BaseModel):
    reference: str = ...  # Path to the context e.g.: sklearn.tree.tree.DecisionTree
    is_a: str = f"{ontology_uri}Context"

    class Config:
        orm_mode = True


class FunctionReferenceModel(BaseModel):
    fn_name: str = ...  # Function name on the given context e.g.: sklearn.tree.tree.DecisionTree.fit
    context: ContextModel = ...  # Context on which function was defined

    class Config:
        orm_mode = True


class CallAccessorModel(FunctionReferenceModel):
    instance_id: int = ...  # Instance id of the instance on which a call was done

    class Config:
        orm_mode = True


class CallIdModel(CallAccessorModel):
    process: int = ...  # Process of the call
    thread: int = ...  # Thread of the call
    instance_number: int = ...  # Number of the call on instance
    call_number: int = ...  # Plain number of the call

    class Config:
        orm_mode = True


class CallModel(RunObjectModel):
    is_a: HttpUrl = f"{ontology_uri}Call"
    call_id: CallIdModel = ...  # Id of the call
    finished: bool = False

    class Config:
        orm_mode = True


class MetadataModel(BaseModel):
    path: str = ...
    description: str = ...
    format: FileFormats = ...


class MetricMetaModel(BaseModel):
    name: str = ...
    description: str = ...
    step: int = ...


class ParameterMetaModel(BaseModel):
    name: str = ...
    description: str = ...
    type: str = ...


class ArtifactMetaModel(BaseModel):
    path: str = ...
    description: str = ...
    format: FileFormats = ...


@dataclass  # No validation
class FileInfo:
    is_dir: bool = ...
    path: str = ...
    file_size: int = ...


class ArtifactInfo(BaseModel):
    meta: ArtifactMetaModel = ...
    file_size: int = ...


class TagMetaModel(BaseModel):
    name: str = ...
    description: str = ...


class LoggerCallModel(RunObjectModel):
    """
    Holds meta data about a logger execution
    """
    failed: Optional[str] = None
    created_by: str = ...  # path to json of LoggerModel
    execution_time: Optional[float] = ...
    output: Optional[str] = ...  # path to json of the OutputModel of the logger
    is_a: HttpUrl = f"{ontology_uri}LoggerCall"

    class Config:
        orm_mode = True


class InjectionLoggerCallModel(LoggerCallModel):
    """
    Holds meta data about an injection logger execution
    """
    pre_time: Optional[float] = ...
    post_time: Optional[float] = ...
    child_time: Optional[float] = ...
    original_call: CallModel = ...  # Triggered by following call
    is_a: HttpUrl = f"{ontology_uri}InjectionLoggerCall"
    execution_time: Optional[float] = None

    @root_validator
    def set_default_execution_time(cls, values):
        if values['execution_time'] is None:
            if values['pre_time'] is not None and values['post_time'] is not None:
                values['execution_time'] = values['pre_time'] + values['post_time']
        return values

    class Config:
        orm_mode = True


class MultiInjectionLoggerCallModel(InjectionLoggerCallModel):
    """Holds meta data about an injection logger multiple execution"""
    call_stack: List[CallModel] = ...
    pre_time: Optional[float] = 0.0
    post_time: Optional[float] = 0.0
    child_time: Optional[float] = 0.0
    is_a: HttpUrl = f"{ontology_uri}MultiInjectionLoggerCall"

    class Config:
        orm_mode = True


class OutputModel(RunObjectModel):
    is_a: HttpUrl = f"{ontology_uri}LoggerOutput"
    additional_data: Optional[dict] = {}

    failed: Optional[str] = None

    class Config:
        orm_mode = True


class EmptyOutput(OutputModel):
    is_a: HttpUrl = f"{ontology_uri}EmptyLoggerOutput"

    class Config:
        orm_mode = True


class TrackedObjectModel(RunObjectModel):
    """
    Data of a tracking object.
    """
    tracked_by: LoggerCallModel = ...

    class Config:
        orm_mode = True
