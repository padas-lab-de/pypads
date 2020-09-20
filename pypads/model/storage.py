from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel

from pypads.model.domain import RunObjectModel
from pypads.utils.logging_util import FileFormats


class MetadataModel(RunObjectModel):
    description: str = ...
    additional_data: Optional[dict] = {}


class MetricMetaModel(MetadataModel):
    name: str = ...
    step: int = ...


class ParameterMetaModel(MetadataModel):
    name: str = ...
    value_format: str = ...


class ArtifactMetaModel(MetadataModel):
    path: str = ...
    file_format: FileFormats = ...


class TagMetaModel(MetadataModel):
    name: str = ...
    value_format: str = ...


@dataclass  # No validation
class FileInfo:
    is_dir: bool = ...
    path: str = ...
    file_size: int = ...


class MetricInfo(BaseModel):
    meta: MetricMetaModel = ...
    # value = ...  # TODO load on access?


class ParameterInfo(BaseModel):
    meta: ParameterMetaModel = ...
    # value = ...  # TODO load on access?


class ArtifactInfo(BaseModel):
    meta: ArtifactMetaModel = ...
    file_size: int = ...
    # content = ...  # TODO load on access?


class TagInfo(BaseModel):
    meta: TagMetaModel = ...
    # value: ...   # TODO load on access?
