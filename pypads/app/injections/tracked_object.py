from abc import ABCMeta
from typing import Type, Union

from pydantic import BaseModel

from pypads.app.env import LoggerEnv
from pypads.app.misc.inheritance import SuperStop
from pypads.model.logger_call import LoggerCallModel
from pypads.model.logger_model import LoggerModel
from pypads.model.logger_output import TrackedObjectModel, OutputModel, ResultHolderModel, ProducedModel, \
    MetricMetaModel, ParameterMetaModel, ArtifactMetaModel, TagMetaModel, ResultModel
from pypads.model.metadata import ModelObject
from pypads.model.mixins import ProvenanceMixin
from pypads.model.models import ResultType, Entry
from pypads.utils.logging_util import FileFormats


class FallibleMixin(ModelObject, SuperStop, metaclass=ABCMeta):
    """
    Something which might be broken / incomplete but still logged due to an error
    """

    def __init__(self, *args, **kwargs):
        self._failed = None
        super().__init__(*args, **kwargs)

    def set_failure_state(self, e: Exception):
        self._failed(f"Logger Output might be inaccurate/corrupt due to exception in execution: '{str(e)}'")

    @property
    def failed(self):
        return self._failed

    @failed.setter
    def failed(self, value):
        self._failed = value


class LoggerCall(FallibleMixin, ProvenanceMixin):
    """
    A single call of a logger.
    """

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return LoggerCallModel

    def __init__(self, *args, logging_env: LoggerEnv, output=None, creator: LoggerModel, **kwargs):
        super().__init__(*args, output=output, **kwargs)
        self.creator = creator
        self.creator_type = creator.storage_type
        self.created_by = self.creator.typed_id()
        self._logging_env = logging_env

    def finish(self):
        self.finished = True

    def store(self):
        self.store_lib()
        from pypads.app.pypads import get_current_pads
        return get_current_pads().backend.log(self)


class ProducedMixin(ModelObject, SuperStop, metaclass=ABCMeta):
    """
    Object being produced by some logger.
    """

    def __init__(self, *args, producer: Union['LoggerCall', LoggerCallModel], **kwargs):
        self._producer = producer
        super().__init__(*args, **kwargs)

    @property
    def producer(self: Union['ProducedMixin', ProducedModel]):
        return self._producer

    @property
    def produced_by(self: Union['ProducedMixin', ProducedModel]):
        return self._producer.typed_id()

    @property
    def producer_type(self: Union['ProducedMixin', ProducedModel]):
        return self._producer.storage_type

    def store(self: Union['ResultHolderMixin', Entry]):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        return pads.backend.log(self)


class ResultHolderMixin(ProducedMixin, ModelObject, SuperStop, metaclass=ABCMeta):
    """
    Object holding some results.
    """

    def __init__(self, *args, **kwargs):
        self._results = {}
        super().__init__(*args, **kwargs)

    def add_result(self, obj: Entry):
        if obj.storage_type not in self._results:
            self._results[obj.storage_type] = set()
        self._results[obj.storage_type].add(obj)

    @property
    def artifacts(self):
        return [a.typed_id() for a in
                self._results[ResultType.artifact]] if ResultType.artifact in self._results else []

    @property
    def parameters(self):
        return [a.typed_id() for a in
                self._results[ResultType.parameter]] if ResultType.parameter in self._results else []

    @property
    def tags(self):
        return [a.typed_id() for a in self._results[ResultType.tag]] if ResultType.tag in self._results else []

    @property
    def metrics(self):
        return [a.typed_id() for a in self._results[ResultType.metric]] if ResultType.metric in self._results else []

    @property
    def tracked_objects(self):
        return [a.typed_id() for a in
                self._results[ResultType.tracked_object]] if ResultType.tracked_object in self._results else []

    def store_metric(self: Union['ResultHolderMixin', ResultHolderModel], key, value, description="", step=None,
                     additional_data: dict = None):
        """
        Function to store a metric relevant to this logger.
        """
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        return pads.api.log_metric(key, value, description=description, step=step, additional_data=additional_data,
                                   holder=self)

    def store_param(self: Union['ResultHolderMixin', ResultHolderModel], key, value, param_type=None, description="",
                    additional_data: dict = None):
        """
        Function to store a parameter relevant to this logger.
        """
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        return pads.api.log_param(key, value, value_format=param_type, description=description,
                                  additional_data=additional_data,
                                  holder=self)

    def store_artifact(self: Union['ResultHolderMixin', ResultHolderModel], local_path, artifact_path,
                       description="", additional_data: dict = None):
        """
        Function to store a artifact relevant to this logger.
        """
        from pypads.app.pypads import get_current_pads
        return get_current_pads().api.log_artifact(local_path, artifact_path=artifact_path,
                                                   description=description,
                                                   additional_data=additional_data, holder=self)

    def store_mem_artifact(self: Union['ResultHolderMixin', ResultHolderModel], path, obj,
                           write_format=FileFormats.text,
                           description="", additional_data: dict = None):
        """
        Function to store a artifact relevant to this logger.
        """
        from pypads.app.pypads import get_current_pads
        return get_current_pads().api.log_mem_artifact(path, obj, write_format=write_format, description=description,
                                                       additional_data=additional_data, holder=self)

    def store_tag(self: Union['ResultHolderMixin', ResultHolderModel], key, value, value_format="string",
                  description="",
                  additional_data: dict = None):
        """
        Function to store a tag relevant to this logger.
        """
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        return pads.api.set_tag(key, value, value_format=value_format, description=description,
                                additional_data=additional_data,
                                holder=self)


class LoggerOutput(FallibleMixin, ProvenanceMixin, ResultHolderMixin):
    """
    The results produced by a single logger.
    """

    def __init__(self, _pypads_env, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._envs = [_pypads_env]

    def add_call_env(self, _pypads_env: LoggerEnv):
        self._envs.append(_pypads_env)

    @property
    def envs(self):
        """
        Stored environments used to produce the output.
        :return:
        """
        return self._envs

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return OutputModel

    def store(self):
        self.store_lib()
        return super().store()


class ChildResultMixin(ProducedMixin, SuperStop, metaclass=ABCMeta):

    def __init__(self, *args, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        self._parent = parent
        super().__init__(*args, **kwargs)

    @property
    def parent(self: Union['ChildResultMixin', ResultModel]):
        return self._parent

    @property
    def part_of(self: Union['ChildResultMixin', ResultModel]):
        return self.parent.typed_id()

    @property
    def parent_type(self: Union['ChildResultMixin', ResultModel]):
        return self.parent.storage_type

    def store(self: Union['ChildResultMixin', Entry]):
        self.parent.add_result(self)
        return super().store()


class ChildResultHolderMixin(ChildResultMixin, ResultHolderMixin, SuperStop, metaclass=ABCMeta):
    """
    Object holding some results and being itself a result object
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TrackedObject(ChildResultHolderMixin, ProvenanceMixin):
    """
    A conceptualized collection of tracked values.
    """

    def __init__(self, *args, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        super().__init__(*args, parent=parent, producer=parent.producer, **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return TrackedObjectModel

    def store(self):
        self.store_lib()
        return super().store()


class MetricTO(ChildResultMixin, ModelObject, SuperStop):
    """
    Metric Tracking Object to be stored in MongoDB itself. The data value is mirrored into mlflow.
    """

    def __init__(self, *args, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        super().__init__(*args, parent=parent, producer=parent.producer, **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return MetricMetaModel


class ParameterTO(ChildResultMixin, ModelObject, SuperStop):
    """
    Parameter Tracking Object to be stored in MongoDB itself. The data value is mirrored into mlflow.
    """

    def __init__(self, *args, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        super().__init__(*args, parent=parent, producer=parent.producer, **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return ParameterMetaModel


class ArtifactTO(ChildResultMixin, ModelObject, SuperStop):
    """
    Artifact to be stored into MongoDB the content is just a path reference to the artifact in mlflow.
    """

    def __init__(self, *args, content=None, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        super().__init__(*args, parent=parent, producer=parent.producer, **kwargs)
        self._content = content

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return ArtifactMetaModel

    def content(self: Union['ArtifactTO', ArtifactMetaModel]):
        if self._content is not None:
            return self._content
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        return pads.backend.load_artifact_data(self.run_id, self.data)


class TagTO(ChildResultMixin, ModelObject, SuperStop):
    """
    Tag to be stored in MongoDB the content is generally the tag value store in mlflow.
    """

    def __init__(self, *args, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        super().__init__(*args, parent=parent, producer=parent.producer, **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return TagMetaModel
