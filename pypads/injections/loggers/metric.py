import os
from typing import Union, Type, Optional

from pydantic import HttpUrl, BaseModel

from pypads import logger
from pypads.app.injections.base_logger import TrackedObject
from pypads.app.injections.injection import InjectionLogger
from pypads.arguments import ontology_uri
from pypads.model.models import TrackedObjectModel, ArtifactMetaModel, MetricMetaModel, OutputModel
from pypads.utils.logging_util import FileFormats


class MetricTO(TrackedObject):
    """
    Tracking object for metrics computed in the workflow.
    """

    class MetricModel(TrackedObjectModel):
        uri: HttpUrl = f"{ontology_uri}Metric"

        name: str = ...  # Metric name
        to_artifact: bool = False
        value: Union[MetricMetaModel, ArtifactMetaModel] = ...

        class Config:
            orm_mode = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.MetricModel

    def store_value(self, value, step):
        self.name = self.tracked_by.original_call.call_id.context.container.__name__ + "." + \
                    self.tracked_by.original_call.call_id.wrappee.__name__

        if isinstance(value, float):
            self.value = MetricMetaModel(name=self.name, step=step,
                                         description="The metric returned by {}".format(self.name))
            self._store_metric(value, self.value)
            return True
        else:
            logger.warning("Mlflow metrics have to be doubles. Could log the return value of type '" + str(
                type(
                    value)) + "' of '" + self.name + "' as artifact instead.")
            if self.to_artifact:
                path = os.path.join(self._base_path(), self._get_artifact_path(self.name))
                self.value = ArtifactMetaModel(path=path, description="", format=FileFormats.text)
                self._store_artifact(value, self.value)
                return True
        return False


class MetricILF(InjectionLogger):
    """
    Function logging the wrapped metric function
    """
    name = "Metric Injection Logger"
    uri = f"{ontology_uri}metric-logger"

    class MetricILFOutput(OutputModel):
        # Add additional context information to
        # TODO context: dict = {**{"test": "testVal"}, **OntologyEntry.__field_defaults__["context"]}
        is_a: HttpUrl = f"{ontology_uri}MetricILF-Output"
        metric: Optional[MetricTO.MetricModel] = None

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.MetricILFOutput

    def __post__(self, ctx, *args, _pypads_artifact_fallback=False, _logger_call, _logger_output, _pypads_result, **kwargs):
        """

        :param ctx:
        :param args:
        :param _pypads_artifact_fallback: Write to artifact if metric can not be logged as an double value into mlflow
        :param _pypads_result:
        :param kwargs:
        :return:
        """

        result = _pypads_result
        metric = MetricTO(tracked_by=_logger_call,
                          to_artifact=_pypads_artifact_fallback)

        storable = metric.store_value(result, step=_logger_call.original_call.call_id.call_number)

        if storable:
            metric.store(_logger_output, key="metric")
