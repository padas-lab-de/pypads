import os
from typing import Union, Type

import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log
from pydantic import HttpUrl, BaseModel

from pypads import logger
from pypads.app.injections.base_logger import TrackedObject
from pypads.app.injections.injection import InjectionLogger
from pypads.model.models import TrackedObjectModel, ArtifactMetaModel, MetricMetaModel, OutputModel
from pypads.utils.logging_util import try_write_artifact, WriteFormats


class MetricTO(TrackedObject):
    """
    Tracking object for metrics computed in the workflow.
    """

    class MetricModel(TrackedObjectModel):
        uri: HttpUrl = "https://www.padre-lab.eu/onto/Metric"

        name: str = ...  # Metric name
        to_artifact: bool = False
        value: Union[MetricMetaModel, ArtifactMetaModel] = ...

        class Config:
            orm_mode = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.MetricModel

    def store_metric(self, value, step):
        self.name = self.tracked_by.original_call.call_id.context.container.__name__ + "." + \
                    self.tracked_by.original_call.call_id.wrappee.__name__

        if isinstance(value, float):
            self.value = MetricMetaModel(name=self.name, step=step,
                                         description="The metric returned by {}".format(self.name))
            self._store_metric(value, self.value)
        else:
            logger.warning("Mlflow metrics have to be doubles. Could log the return value of type '" + str(
                type(
                    value)) + "' of '" + self.name + "' as artifact instead.")
            if self.to_artifact:
                path = os.path.join(self._base_path(), self._get_artifact_path(self.name))
                self.value = ArtifactMetaModel(path=path, description="", format=WriteFormats.text)
                self._store_artifact(value, self.value)


class MetricILF(InjectionLogger):
    """
    Function logging the wrapped metric function
    """
    name = "Metric Injection Logger"
    uri = "https://www.padre-lab.eu/onto/metric-logger"

    class MetricILFOutput(OutputModel):
        is_a: HttpUrl = "https://www.padre-lab.eu/onto/MetricILF-Output"
        Metric: MetricTO.get_model_cls() = ...

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

        metric.store_metric(result,step=_logger_call.original_call.call_id.call_number)

        metric.store(_logger_output, key="Metric")

        # if result is not None:
        #     if isinstance(result, float):
        #         try_mlflow_log(mlflow.log_metric,
        #                        _logger_call.original_call.call_id.context.container.__name__ + "." + _logger_call.original_call.call_id.wrappee.__name__ + ".txt",
        #                        result, step=_logger_call.original_call.call_id.call_number)
        #     else:
        #         logger.warning("Mlflow metrics have to be doubles. Could log the return value of type '" + str(
        #             type(
        #                 result)) + "' of '" + _logger_call.original_call.call_id.context.container.__name__ + "." + _logger_call.original_call.call_id.wrappee.__name__ + "' as artifact instead.")
        #
        #         # TODO search callstack for already logged functions and ignore?
        #         if _pypads_artifact_fallback:
        #             logger.info(
        #                 "Logging result if '" + _logger_call.original_call.call_id.context.container.__name__ + "' as artifact.")
        #             try_write_artifact(_logger_call.original_call.call_id.context.container.__name__, str(result),
        #                                WriteFormats.text)
