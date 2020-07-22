import os
import time
import uuid
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl

from pypads.utils.logging_util import WriteFormats
from pypads.utils.util import get_experiment_id, get_run_id


class OntologyEntry(BaseModel):
    """
    Object representing an (potential) entry in a knowledge base
    """
    uri: HttpUrl = ...


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


class ComponentModel(OntologyEntry):
    """
    Base object for components of code. These can be loggers, actuators etc.
    """
    uid: uuid.UUID = Field(default_factory=uuid.uuid4)  # Automatically created uuid for the object
    created_at: float = Field(default_factory=time.time)  # Creation timestamp
    defined_in: LibraryModel = ...  # In which package the object was defined
    is_a: HttpUrl = ...  # A link to a ontology entry describing the concept of the reference object


class RunObject(OntologyEntry):
    """
    Base object for tracked objects that manage metadata. A MetadataEntity manages and id and a dict of metadata.
    The metadata should contain all necessary non-binary data to describe an entity.
    """
    experiment_id: Optional[str] = Field(default_factory=get_experiment_id)
    run_id: Optional[str] = Field(default_factory=get_run_id)
    uid: uuid.UUID = Field(default_factory=uuid.uuid4)

    def store(self):
        """
        Function to store the object as json into an artifact
        :return:
        """
        from pypads.app.pypads import get_current_pads
        from pypads.utils.logging_util import WriteFormats
        get_current_pads().api.log_mem_artifact("{}#{}".format(self.__class__.__name__, self.uid), self.json(),
                                                WriteFormats.json.value,
                                                path=os.path.join(self.__class__.__name__, str(self.uid)))


class LoggerModel(RunObject):
    """
    A reference object for a logger.
    """
    name: str = "GenericTrackingFunction"
    uid: uuid.UUID = Field(default_factory=uuid.uuid4)
    uri: HttpUrl = "https://www.padre-lab.eu/onto/generic-tracking-function"
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
    uri: HttpUrl = "https://www.padre-lab.eu/onto/generic-run-logger"
    class Config:
        orm_mode = True


class InjectionLoggerModel(LoggerModel):
    """
    Tracking function being exectured on injection hook execution
    """
    name: str = "GenericInjectionLogger"
    uri: HttpUrl = "https://www.padre-lab.eu/onto/generic-injection-logger"

    class Config:
        orm_mode = True


class ContextModel(BaseModel):
    reference: str = ...  # Path to the context e.g.: sklearn.tree.tree.DecisionTree

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


class CallModel(RunObject):
    is_a: HttpUrl = "https://www.padre-lab.eu/onto/Call"
    call_id: CallIdModel = ...  # Id of the call
    finished: bool = False

    class Config:
        orm_mode = True


class MetricMetaModel(BaseModel):
    name: str = ...
    description: str = ...


class ParameterMetaModel(BaseModel):
    name: str = ...
    description: str = ...
    step: int = ...
    type: str = ...


class ArtifactMetaModel(BaseModel):
    path: str = ...
    description: str = ...
    format: WriteFormats = ...


class TagMetaModel(BaseModel):
    name: str = ...
    description: str = ...


class TrackedComponentModel(BaseModel):
    tracking_component: str = ...  # Path to json describing the tracking component
    metrics: List[MetricMetaModel] = []  # Paths of the metrics meta related to the call model
    parameters: List[ParameterMetaModel] = []  # Paths of the parameters related to the call model
    artifacts: List[ArtifactMetaModel] = []  # Paths of the artifacts related to the call model


class LoggerOutputModel(RunObject):
    objects: List[TrackedComponentModel] = []
    is_a: HttpUrl = "https://www.padre-lab.eu/onto/LoggerOutput"

    def store_tracked_object(self, cls, *args, **kwargs):
        tracked_object = cls(*args, **kwargs)
        storage_model = tracked_object.store()
        self.objects.append(storage_model)


class LoggerCallModel(RunObject):
    """
    Holds meta data about a logger execution
    """
    created_by: LoggerModel
    execution_time: float = ...
    output: Optional[LoggerOutputModel] = ...  # Outputs of the logger
    is_a: HttpUrl = "https://www.padre-lab.eu/onto/LoggerCall"

    class Config:
        orm_mode = True


class InjectionLoggerCallModel(LoggerCallModel):
    """
    Holds meta data about an injection logger execution
    """
    created_by: InjectionLoggerModel
    pre_time: float = ...
    post_time: float = ...
    child_time: float = ...
    original_call: CallModel = ...  # Triggered by following call
    is_a: HttpUrl = "https://www.padre-lab.eu/onto/InjectionLoggerCall"

    class Config:
        orm_mode = True


class TrackedObjectModel(RunObject):
    """
    Data of a tracking object.
    """
    tracked_by: LoggerCallModel = ...

    class Config:
        orm_mode = True
