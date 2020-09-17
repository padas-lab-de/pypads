import os
import time
import uuid
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, root_validator

from pypads.arguments import ontology_uri
from pypads.model.models import OntologyEntry
from pypads.utils.logging_util import FileFormats
from pypads.utils.util import get_experiment_id, get_run_id


class LibraryModel(OntologyEntry):
    """
    Representation of a package or library
    """
    is_a: str = f"{ontology_uri}Software"
    name: str = ...
    version: str = ...
    extracted: bool = False
    uri: HttpUrl = None

    @root_validator
    def set_default_uri(cls, values):
        if values['uri'] is None:
            values['uri'] = f"{values['is_a']}#{values['name']}"
        return values


class LibSelectorModel(BaseModel):
    """
    Representation of a selector for a package of library
    """
    name: str = ...  # Name of the package. Either a direct string or a regex.
    constraint: str  # Constraint for the version number
    regex: bool = False  # Flag if the name of the selector is to be considered as a regex
    specificity: int  # How specific the selector is ( important for a css like mapping of multiple selectors)

    def __hash__(self):
        return hash((self.name, self.constraint, self.specificity))

    class Config:
        orm_mode = True


# class ExperimentModel(OntologyEntry):  # TODO
#     """
#     Model of the Experiment
#     """
#     name: str = ...
#     experiment = ...
#
#
# class RunModel(OntologyEntry):  # TODO
#     id: str = ...
#     name: str = ...
#     run = ...


class RunObjectModel(BaseModel):
    """
    Base object for tracked objects that manage metadata. A MetadataEntity manages and id and a dict of metadata.
    The metadata should contain all necessary non-binary data to describe an entity.
    """
    experiment_id: Optional[str] = Field(default_factory=get_experiment_id)
    run_id: Optional[str] = Field(default_factory=get_run_id)
    uid: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: float = Field(default_factory=time.time)

    def store(self):
        """
        Function to store the object as json into an artifact
        :return:
        """
        from pypads.app.pypads import get_current_pads
        get_current_pads().api.log_mem_artifact(os.path.join(self.__class__.__name__, str(self.uid)),
                                                self.json(by_alias=True),
                                                write_format=FileFormats.json)
