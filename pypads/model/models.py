import time
import uuid
from abc import abstractmethod
from enum import Enum
from typing import Union, Optional

import pydantic
from pydantic import BaseModel, Field

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


class EntryModel(BaseModel):
    clazz: str = None  # Class of the model
    storage_type: Union[ResultType, str] = ...  # Should generally be one of ResultType

    @pydantic.validator('clazz', pre=True, always=True)
    def default_ts_modified(cls, v, *, values, **kwargs):
        if v is None:
            return str(cls)
        return v


class RunObjectModel(BaseModel):
    backend_uri: Optional[str] = Field(default_factory=get_backend_uri)
    experiment_id: Optional[str] = Field(default_factory=get_experiment_id)
    experiment_name: Optional[str] = Field(default_factory=get_experiment_name)
    run_id: Optional[str] = Field(default_factory=get_run_id)


class CreatedAtModel(BaseModel):
    created_at: float = Field(default_factory=time.time)


class BaseIdModel(RunObjectModel, EntryModel):
    uid: Union[str, uuid.UUID] = Field(default_factory=uuid.uuid4)

    def __hash__(self):
        return persistent_hash((self.clazz, self.backend_uri, self.experiment_id, self.run_id, self.uid))


class IdBasedModel(BaseIdModel):
    id: str = Field(alias="_id", default=None)

    def get_reference(self):
        return get_reference(self)

    @pydantic.validator('id', pre=True, always=True)
    def default_ts_modified(cls, v, *, values, **kwargs):
        if v is not None:
            return v
        else:
            reference_class = get_reference_class(values)
            return to_reference(
                {k: values[k] for k in values.keys() if k in reference_class.__fields__.keys()}).__hash__()


class BaseStorageModel(CreatedAtModel, IdBasedModel):
    category: str = ...  # Human readable class representation. This will be converted in ontology entries.
    uid: Union[str, uuid.UUID] = Field(default_factory=uuid.uuid4)


class Reference:

    @abstractmethod
    def load(self):
        raise NotImplementedError()


class IdReference(Reference, BaseIdModel):
    id: str = Field(alias="_id", default=None)

    @pydantic.validator('id', always=True)
    def default_ts_modified(cls, v, *, values, **kwargs):
        return v or str(persistent_hash(
            (values["clazz"], values["backend_uri"], values["experiment_id"], values["run_id"], values["uid"])))

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
            return pads.backend.get_by_path(self.run_id, self.path)
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
    if reference_class is None:
        reference_class = get_reference_class(obj)
    # Get fields of the object
    if isinstance(obj, BaseModel):
        return reference_class.construct(**obj.dict())
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
    _in = _has_checker(dict_or_obj)
    if _in("path"):
        return PathReference
    else:
        return IdReference


def _has_checker(dict_or_obj):
    if isinstance(dict_or_obj, dict):
        def _in(key):
            return key in dict_or_obj

        return _in
    else:
        def _hasattr(key):
            return hasattr(dict_or_obj, key)

        return _hasattr
