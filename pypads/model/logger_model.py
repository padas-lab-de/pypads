import uuid
from typing import List, Union

from pypads.model.domain import LibSelectorModel
from pypads.model.models import BaseStorageModel, ResultType, ProvenanceModel


class LoggerModel(ProvenanceModel, BaseStorageModel):
    """
    A reference object for a logger.
    """
    name: str = "Generic Tracking Function"
    schema_location: str = ...
    uid: Union[str, uuid.UUID] = ...
    category: str = "Logger"
    dependencies: List[LibSelectorModel] = []
    supported_libraries: List[LibSelectorModel] = ...
    allow_nested: bool = True
    allow_intermediate: bool = True
    storage_type: Union[str, ResultType] = ResultType.logger

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
