from typing import Optional

from pypads.model.models import IdBasedEntry


class OutputModel(IdBasedEntry):
    category: str = "LoggerOutput"
    additional_data: Optional[dict] = ...
    name: str = "Output"
    produced_by: str = ...  # reference to the logger call

    class Config:
        orm_mode = True


class TrackedObjectModel(IdBasedEntry):
    """
    Data of a tracking object.
    """
    category: str = "TrackedObject"
    name: str = "GenericTrackedObject"
    part_of: str = ...  # reference to the logger_output

    class Config:
        orm_mode = True
