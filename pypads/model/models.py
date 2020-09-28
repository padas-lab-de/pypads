import uuid

from pydantic import BaseModel, Field, root_validator


class Entry(BaseModel):
    clazz: str = None  # Class of the model
    category: str = ...  # Human readable class representation. This will be converted in ontology entries.

    @root_validator
    def set_default(cls, values):
        if values['clazz'] is None:
            values['clazz'] = str(cls)
        return values


class IdBasedEntry(Entry):
    uid: uuid.UUID = Field(default_factory=uuid.uuid4)
