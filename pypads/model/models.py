import time
import uuid
from abc import abstractmethod
from enum import Enum
from typing import Union, Optional

import pydantic
from pydantic import BaseModel, Field, root_validator

from pypads import logger
from pypads.utils.util import get_backend_uri, get_experiment_id, get_experiment_name, get_run_id, persistent_hash


class ResultType(Enum):
    artifact = 'artifact'
    parameter = 'parameter'
    metric = 'metric'
    tag = 'tag'
    repository_entry = 'repository_entry'  # This represents a repository itself it normally is not persisted.
    tracked_object = 'tracked_object'
    output = 'output'
    logger_call = 'loggerCall'
    logger = 'logger'
    schema = 'schema'
    library = 'library'
    mapping = 'mapping'
    embedded = 'embedded'  # This entry is not to be stored itself in an own document. It should be embedded into others


class AbstractionType(Enum):
    reference = 'reference'  # This object represents only a reference to the described object
    value = 'value'  # This object represents only the contained value and a reference to the described object


class EntryModel(BaseModel):
    clazz: str = None  # Class of the model
    abstraction_type: Optional[AbstractionType] = None  # This optional field can represent an abstraction or view level
    # to inform the storing backend about the state of the object. This can be important for dereferencing rdf
    # from the objects or future object update policies
    storage_type: Union[ResultType, str] = ...  # Should generally be one of ResultType

    @pydantic.validator('clazz', pre=True, always=True)
    def default_ts_modified(cls, v, *, values, **kwargs):
        if v is None:
            return str(cls)
        return v


class BackendObjectModel(BaseModel):
    backend_uri: Optional[str] = Field(default_factory=get_backend_uri)


class ExperimentModel(BackendObjectModel):
    uid: str = Field(default_factory=get_experiment_id)
    name: str = Field(default_factory=get_experiment_name)
    category: str = "Experiment"


class RunModel(BackendObjectModel):
    uid: str = Field(default_factory=get_run_id)
    category: str = "Run"


class Reference(BaseModel):
    abstraction_type: AbstractionType = None

    @pydantic.validator('abstraction_type', always=True)
    def default_ts_modified(cls, v, *, values, **kwargs):
        return v or AbstractionType.reference

    @abstractmethod
    def load(self):
        raise NotImplementedError()


class RunReference(Reference, RunModel):

    def load(self):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        return pads.api.get_run(self.uid)


class ExperimentReference(Reference, ExperimentModel):

    def load(self):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        return pads.api.get_experiment(self.uid)


class RunObjectModel(BackendObjectModel):
    experiment: Optional[ExperimentReference] = Field(
        default_factory=lambda: get_reference(ExperimentModel()) if get_experiment_id() is not None else None)
    run: Optional[RunReference] = Field(
        default_factory=lambda: get_reference(RunModel()) if get_run_id() is not None else None)


class CreatedAtModel(BaseModel):
    created_at: float = Field(default_factory=time.time)


class BaseIdModel(EntryModel, BackendObjectModel):
    """
    Model used for entries defining an own uid value.
    """
    uid: Union[str, uuid.UUID] = Field(default_factory=uuid.uuid4)

    def __hash__(self):
        return persistent_hash((self.clazz, self.backend_uri, self.uid))


class IdHashModel(BaseIdModel):
    """
    Model used for entries compiling a composite id from the uid and other attributes via their reference.
    """
    id: str = Field(alias="_id", default=None)

    def get_reference(self):
        return get_reference(self)

    @root_validator
    def default_ts_modified(cls, values):
        if 'id' not in values or values['id'] is None:
            reference_class = get_reference_class(values)
            values['id'] = str(to_reference(
                {k: values[k] for k in values.keys() if k in reference_class.__fields__.keys()}).__hash__())
        return values


class BaseStorageModel(RunObjectModel, CreatedAtModel, IdHashModel):
    category: str = ...  # Human readable class representation. This will be converted in ontology entries.
    uid: Union[str, uuid.UUID] = Field(default_factory=uuid.uuid4)


class IdReference(Reference, RunObjectModel, BaseIdModel):
    id: str = Field(alias="_id", default=None)
    category: Optional[str]

    @pydantic.validator('id', always=True)
    def default_ts_modified(cls, v, *, values, **kwargs):
        return v or str(persistent_hash(
            (values["clazz"], values["backend_uri"], values["uid"])))

    def load(self):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        if self.backend_uri is not pads.backend.uri:
            # TODO init backend if possible?
            logger.error("Can't load object due to unavailable backend.")
            return None
        return pads.backend.get(self.uid, self.storage_type)


class PathReference(IdReference):
    path: str = ...

    def load(self):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        if self.backend_uri is not pads.backend.uri:
            # TODO init backend if possible?
            logger.error("Can't load object due to unavailable backend.")
            return None
        try:
            return pads.backend.get_by_path(self.run.uid, self.path)
        except Exception as e:
            from pypads.app.pypads import get_current_pads
            return pads.backend.get(self.uid, self.storage_type)


class ProvenanceModel(BaseStorageModel):
    defined_in: IdReference = ...


def get_reference_dict(obj, validate=True, reference_class=None):
    if reference_class is None:
        reference_class = get_reference_class(obj)
    return obj.dict(validate=validate, force=True,
                    include={str(k) for k in reference_class.__fields__.keys()})


def get_reference(obj, validate=True, reference_class=None):
    """
    :param reference_class:
    :param obj:
    :param validate: Flag to indicate whether we want to validate input model
    :return:
    """
    if obj is None:
        return None
    from pypads.app.backends.repository import RepositoryObject
    if isinstance(obj, RepositoryObject):
        return obj.get_reference()
    if reference_class is None:
        reference_class = get_reference_class(obj)
    # Get fields of the object
    if isinstance(obj, BaseModel):
        return reference_class(**obj.dict())
    return to_reference(get_reference_dict(obj, validate=validate, reference_class=reference_class),
                        reference_class=reference_class)


def unwrap_typed_id(uid):
    id_splits = uid.split(".")
    return {"uid": id_splits[0], "storage_type": id_splits[1]}


def to_reference(dict_obj, reference_class=None):
    if reference_class is None:
        reference_class = get_reference_class(dict_obj)
    return reference_class(**dict_obj)


def get_reference_class(dict_or_obj):
    _in, _get = _has_checker(dict_or_obj)
    if _in("category"):
        if _get("category") == "Experiment":
            return ExperimentReference
        if _get("category") == "Run":
            return RunReference
    if _in("path"):
        return PathReference
    else:
        return IdReference


def _has_checker(dict_or_obj):
    if isinstance(dict_or_obj, dict):
        def _in(key):
            return key in dict_or_obj

        def _get(key):
            return dict_or_obj[key]

        return _in, _get
    else:
        def _hasattr(key):
            return hasattr(dict_or_obj, key)

        def _get(key):
            return getattr(dict_or_obj, key)

        return _hasattr, _get
