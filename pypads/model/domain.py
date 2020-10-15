import time
from typing import Optional, Union

from pydantic import BaseModel, Field, root_validator

from pypads.model.models import IdBasedEntry, ResultType
from pypads.utils.util import get_experiment_id, get_run_id, get_experiment_name


class LibraryModel(IdBasedEntry):
    """
    Representation of a package or library
    """
    category: str = "Software"
    name: str = ...
    version: str = ...
    extracted: bool = False
    storage_type: Union[str, ResultType] = ResultType.library

    @root_validator
    def set_default(cls, values):
        values['_id'] = ".".join([values["name"], values["version"]])
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


class MappingModel(IdBasedEntry):
    """
    Representation of a mapping of a library
    """
    category: str = "SoftwareMapping"
    name: str = ...
    author: Optional[str] = ...
    version: str = ...
    lib: LibSelectorModel = ...
    mapping_file: Optional[str] = ...  # reference to the mapping file artifact
    storage_type: Union[str, ResultType] = ResultType.mapping

    @root_validator
    def set_default(cls, values):
        values['_id'] = ".".join(
            [values["author"], values["version"], values["lib"].name, values["lib"].constraint])
        return values

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
    experiment_name: Optional[str] = Field(default_factory=get_experiment_name)
    run_id: Optional[str] = Field(default_factory=get_run_id)
    created_at: float = Field(default_factory=time.time)
