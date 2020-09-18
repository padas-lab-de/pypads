from typing import List

from pydantic import HttpUrl

from pypads.arguments import ontology_uri
from pypads.model.domain import LibSelectorModel
from pypads.model.models import OntologyEntry


class LoggerModel(OntologyEntry):
    """
    A reference object for a logger.
    """
    name: str = "GenericTrackingFunction"
    uid: str = ...
    is_a: HttpUrl = f"{ontology_uri}logger"
    dependencies: List[LibSelectorModel] = {}
    supported_libraries: List[LibSelectorModel] = ...
    allow_nested: bool = True
    allow_intermediate: bool = True

    class Config:
        orm_mode = True


class RunLoggerModel(LoggerModel):
    """
    Tracking function being executed on run teardown or setup
    """
    name: str = "GenericRunLogger"
    is_a: HttpUrl = f"{ontology_uri}run-logger"

    class Config:
        orm_mode = True


class InjectionLoggerModel(LoggerModel):
    """
    Tracking function being exectured on injection hook execution
    """
    name: str = "GenericInjectionLogger"
    is_a: HttpUrl = f"{ontology_uri}injection-logger"

    class Config:
        orm_mode = True
