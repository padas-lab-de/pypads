from pydantic import HttpUrl

from pypads.arguments import ontology_uri
from pypads.model.models import IdBasedOntologyEntry, IdBasedEntry


class OutputModel(IdBasedOntologyEntry):
    is_a: HttpUrl = f"{ontology_uri}LoggerOutput"

    class Config:
        orm_mode = True


class TrackedObjectModel(IdBasedOntologyEntry):
    """
    Data of a tracking object.
    """
    is_a: HttpUrl = f"{ontology_uri}TrackedObject"
    tracked_by: IdBasedEntry = ...  # id for the logger_call

    class Config:
        orm_mode = True
