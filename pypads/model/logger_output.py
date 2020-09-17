from pydantic import HttpUrl

from pypads.arguments import ontology_uri
from pypads.model.models import OntologyEntry


class OutputModel(OntologyEntry):
    is_a: HttpUrl = f"{ontology_uri}LoggerOutput"

    class Config:
        orm_mode = True


class EmptyOutput(OutputModel):  # No output for the logger
    is_a: HttpUrl = f"{ontology_uri}EmptyLoggerOutput"

    class Config:
        orm_mode = True


class TrackedObjectModel(OntologyEntry):
    """
    Data of a tracking object.
    """
    tracked_by: str = ...  # Path to logger call

    class Config:
        orm_mode = True
