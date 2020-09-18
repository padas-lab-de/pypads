from typing import Optional, Union, List

from pydantic import HttpUrl

from pypads.arguments import ontology_uri
from pypads.model.models import IdBasedOntologyEntry


class OutputModel(IdBasedOntologyEntry):
    is_a: HttpUrl = f"{ontology_uri}LoggerOutput"
    additional_data: Optional[dict] = ...
    name: str = "Output"
    produced_by: str = ... # reference to the logger call

    class Config:
        orm_mode = True


class TrackedObjectModel(IdBasedOntologyEntry):
    """
    Data of a tracking object.
    """
    is_a: HttpUrl = f"{ontology_uri}TrackedObject"
    # tracked_by: str = ...  # id for the logger_call
    name: str = "TrackedObject"
    part_of : str = ... # reference to the logger_output

    class Config:
        orm_mode = True
