import uuid
from enum import Enum
from typing import Union

from pydantic import BaseModel, Field, root_validator


class ResultType(Enum):
    artifact = 'artifact'
    parameter = 'parameter'
    metric = 'metric'
    tag = 'tag'
    tracked_object = 'tracked_object'
    output = 'output'
    logger_call = 'loggerCall'
    logger = 'logger'
    schema = 'schema'
    library = 'library'


class Entry(BaseModel):
    clazz: str = None  # Class of the model
    category: str = ...  # Human readable class representation. This will be converted in ontology entries.
    storage_type: Union[ResultType, str] = ...  # Should generally be one of ResultType

    @root_validator
    def set_default(cls, values):
        if values['clazz'] is None:
            values['clazz'] = str(cls)
        return values


class IdBasedEntry(Entry):
    uid: uuid.UUID = Field(default_factory=uuid.uuid4)
    _id: str = None

    def typed_id(self):
        return get_typed_id(self)

    @root_validator
    def set_default(cls, values):
        if '_id' not in values or values['_id'] is None:
            values['_id'] = join_typed_id([str(values['uid']),
                                           values['storage_type'].value if isinstance(values['storage_type'],
                                                                                      ResultType) else values[
                                               'storage_type']])
        return values


class ProvenanceModel(Entry):
    defined_in: str = ...


def get_typed_id(obj):
    fragments = []
    if hasattr(obj, "uid"):
        fragments.append(str(obj.uid))
    if hasattr(obj, "storage_type"):
        fragments.append(
            str(obj.storage_type.value) if isinstance(obj.storage_type, ResultType) else obj.storage_type)
    return join_typed_id(fragments)


def unwrap_typed_id(uid):
    id_splits = uid.split(".")
    return {"uid": id_splits[0], "storage_type": id_splits[1]}


def join_typed_id(fragments):
    return ".".join([str(f) for f in fragments])
