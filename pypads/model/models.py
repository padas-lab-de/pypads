import uuid
from enum import Enum
from typing import Union

import pydantic
from pydantic import BaseModel, Field, root_validator


class ResultType(Enum):
    artifact = 'artifact'
    parameter = 'parameter'
    metric = 'metric'
    tag = 'tag'
    repository_entry = 'repository_entry'
    tracked_object = 'tracked_object'
    output = 'output'
    logger_call = 'loggerCall'
    logger = 'logger'
    schema = 'schema'
    library = 'library'
    mapping = 'mapping'
    embedded = 'embedded'  # This entry is not to be stored itself in an own document. It should be embedded into others


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
    uid: Union[str, uuid.UUID] = Field(default_factory=uuid.uuid4)
    id: str = Field(alias="_id", default=None)

    def typed_id(self):
        return get_typed_id(self)

    @pydantic.validator('id', pre=True, always=True)
    def default_ts_modified(cls, v, *, values, **kwargs):
        return v or join_typed_id(
            [str(values['uid']), values['storage_type'].value if isinstance(values['storage_type'],
                                                                            ResultType) else values['storage_type']])


class ProvenanceModel(Entry):
    defined_in: str = ...


def get_typed_id(obj):
    fragments = []
    if hasattr(obj, "uid"):
        fragments.append(str(obj.uid))
    if hasattr(obj, "storage_type"):
        fragments.append(
            str(obj.storage_type.value) if isinstance(obj.storage_type, ResultType) else obj.storage_type)
    # TODO add backend URI
    return join_typed_id(fragments)


def unwrap_typed_id(uid):
    id_splits = uid.split(".")
    return {"uid": id_splits[0], "storage_type": id_splits[1]}


def join_typed_id(fragments):
    return ".".join([str(f) for f in fragments])
