from dataclasses import dataclass
from typing import Optional, List, Union

from pydantic import BaseModel

from pypads.model.domain import RunObjectModel
from pypads.model.models import IdBasedEntry
from pypads.utils.logging_util import FileFormats


def extract_persistent_data(data):
    if "_persistent" in data:
        return data["_persistent"]
    else:
        return {}


class MetadataModel(IdBasedEntry, RunObjectModel):
    description: str = ...
    additional_data: \
        Optional[dict] = {}  # Additional data should hold all persistent additional data (Defined by _persistent)


class MetricMetaModel(MetadataModel):
    name: str = ...
    step: int = ...
    category: str = "MLMetric"


class ParameterMetaModel(MetadataModel):
    name: str = ...
    value_format: str = ...
    category: str = "HyperParameter"


class ArtifactMetaModel(MetadataModel):
    path: str = ...
    file_format: FileFormats = ...
    category: str = "Artifact"
    type: Optional[str] = ...


class TagMetaModel(MetadataModel):
    category: str = "MLTag"
    name: str = ...
    value_format: str = ...


@dataclass  # No validation
class FileInfo:
    is_dir: bool = ...
    path: str = ...
    file_size: int = ...


class MetricInfo(BaseModel):
    meta: MetricMetaModel = ...
    content: Union[str, List] = ...


class ParameterInfo(BaseModel):
    meta: ParameterMetaModel = ...
    content: str = ...

@dataclass
class ArtifactInfo:
    meta: ArtifactMetaModel = ...
    file_size: int = ...

    def content(self):
        from pypads.app.pypads import get_current_pads
        return get_current_pads().results.load_artifact(relative_path=self.meta.path, run_id=self.meta.run_id,
                                                    read_format=self.meta.file_format)


class TagInfo(BaseModel):
    meta: TagMetaModel = ...
    content: str = ...
