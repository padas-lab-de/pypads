import os
import time
import uuid
from collections import deque
from typing import List, Optional

import mlflow
from pydantic import ValidationError, BaseModel, Field, AnyUrl, validate_model

from pypads.app.misc.inheritance import SuperStop
from pypads.utils.logging_util import WriteFormats


class ValidationErrorHandler:
    """ Class to handle errors on the validation of an validatable. """

    def __init__(self, absolute_path=None, validator=None, handle=None):
        self._absolute_path = absolute_path
        self._validator = validator
        self._handle = handle

    @property
    def validator(self):
        return self._validator

    @property
    def absolute_path(self):
        return self._absolute_path

    def handle(self, cls, e, options):
        if (not self._absolute_path or deque(self._absolute_path) == e.absolute_path) and (
                not self._validator or self.validator == e.validator):
            if self._handle is None:
                self._default_handle(e)
            else:
                return self._handle(cls, e, options)
        else:
            raise e

    def _default_handle(self, e):
        print("Empty validation handler triggered: " + str(self))
        raise e


class ValidateableFactory:

    @staticmethod
    def from_object(cls: BaseModel, obj, handlers: List[ValidationErrorHandler] = None):
        return ValidateableFactory._try_creation(cls, cls.from_orm, handlers=handlers, __history=[], obj=obj)

    @staticmethod
    def make(cls, *args, handlers: List[ValidationErrorHandler] = None, **options):
        return ValidateableFactory._try_creation(cls, cls, *args, handlers=handlers, __history=[], **options)

    @staticmethod
    def _try_creation(cls, fn, *args, handlers: List[ValidationErrorHandler] = None, __history=None, **options):
        if handlers is None:
            handlers = []
        try:
            return fn(*args, **options)
        except ValidationError as e:
            # Raise error if we can't handle anything
            if handlers is None:
                raise e
            for handler in handlers:
                new_options = handler.handle(cls, e, options)
                # If the handler could fix the problem return the new value
                if new_options is not None and e not in __history and new_options not in __history:
                    __history.append(e)
                    __history.append(new_options)

                    # Try to create object again
                    return ValidateableFactory._try_creation(cls, handlers=handlers, __history=__history, **new_options)
            # Raise error if we fail
            raise e


def get_experiment_id():
    if mlflow.active_run():
        return mlflow.active_run().info.experiment_id
    return None


def get_run_id():
    if mlflow.active_run():
        return mlflow.active_run().info.run_id
    return None


class ReferenceObject(BaseModel):
    """
    Base object for tracked objects that manage metadata. A MetadataEntity manages and id and a dict of metadata.
    The metadata should contain all necessary non-binary data to describe an entity.
    """

    uid: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: float = Field(default_factory=time.time)
    experiment_id: Optional[str] = Field(default_factory=get_experiment_id)
    run_id: Optional[str] = Field(default_factory=get_run_id)

    def store(self):
        from pypads.app.pypads import get_current_pads
        from pypads.utils.logging_util import WriteFormats
        get_current_pads().api.log_mem_artifact(self.uid, self.json(), WriteFormats.json.value,
                                                path=os.path.join(self.__class__.__name__, str(self.uid)))


class MetadataObject(SuperStop):
    """
    Used for objects representing a validateable base model
    """

    def __init__(self, *args, model_cls, **kwargs):
        super().__init__(*args, **kwargs)
        self._model_cls = model_cls

        fields = set(self._model_cls.__fields__.keys())

        # Add given fields to metadata object if not already existing
        for key, val in kwargs.items():
            if key in fields and not self._has_direct_attr(key):
                setattr(self, key, val)
                fields.remove(key)

        # Add defaults which are not given
        for key in fields:
            if not self._has_direct_attr(key) and self._model_cls.__fields__:
                setattr(self, key, self._model_cls.__fields__[key].get_default())

    def _has_direct_attr(self, name):
        try:
            object.__getattribute__(self, name)
            return True
        except AttributeError:
            return False

    def validate(self):
        validate_model(self._model_cls, self.model())

    def model(self):
        return self._model_cls.from_orm(self)

    def schema(self):
        return self._model_cls.schema()

    def json(self):
        return self._model_cls.from_orm(self).json()


class MetadataHolder(MetadataObject):
    """
    Used for objects storing their information directly into a validated base model
    """

    def __init__(self, *args, model_cls, model: ReferenceObject = None, **kwargs):
        self._model = model_cls(*args, **kwargs) if model is None else model
        super().__init__(*args, model_cls=model_cls, **kwargs)

    def __getattr__(self, name):
        if name not in ["_model", "_model_cls"] and name in self._model.__fields__.keys():
            return getattr(self._model, name)
        else:
            return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if name not in ["_model", "_model_cls"] and name in self._model.__fields__.keys():
            setattr(self._model, name, value)
        else:
            return object.__setattr__(self, name, value)

    def model(self):
        return self._model


class LibSelectorModel(BaseModel):
    """
    Data of a lib selector
    """
    name: str = ...
    constraint: str
    regex: bool = False
    specificity: int

    def __hash__(self):
        return hash((self.name, self.constraint, self.specificity))

    class Config:
        orm_mode = True


class LoggerModel(BaseModel):
    """
    Holds meta data about a logger
    """
    uid: uuid.UUID = Field(default_factory=uuid.uuid4)
    url: AnyUrl = "https://www.padre-lab.eu/onto/generic-logger"
    name: str = "GenericLogger"
    dependencies: List[LibSelectorModel] = {}
    supported_libraries: List[LibSelectorModel] = ...
    allow_nested: bool = True
    allow_intermediate: bool = True
    static_parameters: dict = {}

    class Config:
        orm_mode = True

    # def store(self):
    #     from pypads.app.pypads import get_current_pads
    #     from pypads.utils.logging_util import WriteFormats
    #     get_current_pads().api.log_mem_artifact(self.uid, self.json(), WriteFormats.json.value,
    #                                             path="loggers")


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


class CallModel(ReferenceObject):
    # TODO more data needed?
    call_id: CallIdModel = ...  # Id of the call

    class Config:
        orm_mode = True


class MetricMetaModel(BaseModel):
    name: str = ...
    description: str = ...


class ParameterMetaModel(BaseModel):
    name: str = ...
    description: str = ...
    type: str = ...


class ArtifactMetaModel(BaseModel):
    path: str = ...
    description: str = ...
    format: WriteFormats = ...


class TrackedComponentModel(BaseModel):
    tracking_component: str = ...  # Path to json describing the tracking component
    metrics: List[MetricMetaModel] = []  # Paths of the metrics meta related to the call model
    parameters: List[ParameterMetaModel] = []  # Paths of the parameters related to the call model
    artifacts: List[ArtifactMetaModel] = []  # Paths of the artifacts related to the call model


class LoggerOutputModel(ReferenceObject):
    objects: List[TrackedComponentModel] = []

    def store_tracked_object(self, cls, *args, **kwargs):
        tracked_object = cls(*args, **kwargs)
        storage_model = tracked_object.store()
        self.objects.append(storage_model)


class LoggerCallModel(ReferenceObject):
    """
    Holds meta data about a logger call
    """
    logger_meta: LoggerModel
    pre_time: float = ...
    post_time: float = ...
    child_time: float = ...
    call: CallModel = ...  # Triggered by following call
    output: Optional[LoggerOutputModel] = ...  # Outputs of the logger

    # tracked_by: str = ...

    class Config:
        orm_mode = True
