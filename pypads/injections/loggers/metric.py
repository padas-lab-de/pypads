from typing import Type, Optional, Union
from uuid import UUID

from pydantic import BaseModel

from pypads import logger
from pypads.app.env import InjectionLoggerEnv
from pypads.app.injections.injection import InjectionLogger
from pypads.app.injections.tracked_object import TrackedObject
from pypads.model.logger_output import OutputModel, TrackedObjectModel


class MetricTO(TrackedObject):
    """
    Tracking object for metrics computed in the workflow.
    """

    class MetricModel(TrackedObjectModel):
        category: str = "Metric"
        description = "A tracked metric of the experiment."

        name: str = ...  # Metric name
        as_artifact: bool = False

        class Config:
            orm_mode = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.MetricModel

    def store_value(self, value, step, name=""):
        self.name = self.producer.original_call.call_id.context.container.__name__ + "." + \
                    self.producer.original_call.call_id.wrappee.__name__ + "." + name

        if isinstance(value, float):
            self.store_metric(self.name, value, description="The metric returned by {}".format(self.name), step=step)
            return True
        else:
            logger.warning("Mlflow metrics have to be doubles. Could log the return value of type '" + str(
                type(
                    value)) + "' of '" + self.name + "' as artifact instead.")
            if self.as_artifact:
                self.name = self.store_mem_artifact(self.name, value,
                                                    description="The metric returned by {}".format(self.name))
                return True
        return False


class MetricILF(InjectionLogger):
    """
    Function logging the wrapped metric function
    """
    name = "Metric Injection Logger"
    category: str = "MetricLogger"

    class MetricILFOutput(OutputModel):
        # Add additional context information to
        # TODO context: dict = {**{"tests": "testVal"}, **OntologyEntry.__field_defaults__["context"]}
        category: str = "MetricILF-Output"
        metric: Optional[Union[UUID, str]] = None

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.MetricILFOutput

    def __post__(self, ctx, *args, _pypads_env: InjectionLoggerEnv, _pypads_artifact_fallback=False, _logger_call,
                 _logger_output, _pypads_result, **kwargs):
        """

        :param ctx:
        :param args:
        :param _pypads_artifact_fallback: Write to artifact if metric can not be logged as an double value into mlflow
        :param _pypads_result:
        :param kwargs:
        :return:
        """

        result = _pypads_result
        metric = MetricTO(parent=_logger_output,
                          as_artifact=_pypads_artifact_fallback, additional_data=_pypads_env.data)

        storable = metric.store_value(result, step=_logger_call.original_call.call_id.call_number)

        if storable:
            _logger_output.metric = metric.store()
