from typing import List

from pypads.model.domain import LibSelectorModel
from pypads.model.models import IdBasedEntry


class LoggerModel(IdBasedEntry):
    """
    A reference object for a logger.
    """
    name: str = "Generic Tracking Function"
    uid: str = ...
    category: str = "Logger"
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
    name: str = "Generic Run Logger"
    category: str = "RunLogger"

    class Config:
        orm_mode = True


class InjectionLoggerModel(LoggerModel):
    """
    Tracking function being exectured on injection hook execution
    """
    name: str = "Generic Injection Logger"
    category: str = "InjectionLogger"

    class Config:
        orm_mode = True
