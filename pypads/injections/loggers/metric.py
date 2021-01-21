from typing import Type, Optional

from pydantic import BaseModel

from pypads import logger
from pypads.app.env import InjectionLoggerEnv
from pypads.app.injections.injection import InjectionLogger
from pypads.app.injections.tracked_object import TrackedObject
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.model.models import IdReference
from pypads.utils.logging_util import data_path, FileFormats


class MetricTO(TrackedObject):
    """
    Tracking object for metrics computed in the workflow. This allows to hold metrics also as artifacts if needed.
    """

    class MetricTOModel(TrackedObjectModel):
        type: str = "Metric"
        as_artifact: bool = False
        documentation: str = ...
        metric: IdReference = ...

        class Config:
            orm_mode = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.MetricTOModel


class MetricILF(InjectionLogger):
    """
    Function logging the wrapped metric function
    """
    name = "Metric Injection Logger"
    type: str = "MetricLogger"

    class MetricILFOutput(OutputModel):
        # Add additional context information to
        type: str = "MetricILF-Output"
        metric: Optional[IdReference] = None

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.MetricILFOutput

    def __post__(self, ctx, *args, _pypads_env: InjectionLoggerEnv,
                 _pypads_artifact_fallback: Optional[FileFormats] = None, _logger_call,
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

        # Get data from mapping or provided additional data
        # Find / extract name
        name = data_path(_pypads_env.data, "metric", "@schema", "rdfs:label",
                         default=".".join([_logger_output.producer.original_call.call_id.context.container.__name__,
                                           _logger_output.producer.original_call.call_id.wrappee.__name__]))

        # Find / extract description
        not_found_content = "No description found."
        description = data_path(_pypads_env.data, "metric", "@schema", "rdfs:comment",
                                default=getattr(ctx, "__doc__", not_found_content) if ctx else not_found_content)

        # Find / extract step
        step = data_path(_pypads_env.data, "metric", "@schema", "step",
                         default=_logger_call.original_call.call_id.call_number)

        # Find / extract documentation
        documentation = data_path(_pypads_env.data, "metric", "@schema", "padre:documentation",
                                  default=description)

        # Build tracked object
        metric_to = MetricTO(name=name, description=description, step=_logger_call.original_call.call_id.call_number,
                             documentation=documentation,
                             additional_data=_pypads_env.data, parent=_logger_output)

        # Store the value itself
        if isinstance(result, float):
            metric_to.as_artifact = False
            metric_to.metric = metric_to.store_metric(key=name, value=result,
                                                      description="The metric returned by {}".format(self.name),
                                                      step=step, additional_data=_pypads_env.data)
        else:

            # If value is not a valid double
            logger.warning("Mlflow metrics have to be doubles. Could log the return value of type '" + str(
                type(result)) + "' of '" + self.name +
                           "' as artifact instead. Activate with _pypads_artifact_fallback=True")
            if _pypads_artifact_fallback:
                logger.warning("Logging metric as artifact.")
                metric_to.as_artifact = True
                metric_to.metric = metric_to.store_mem_artifact(self.name, result,
                                                                write_format=_pypads_artifact_fallback,
                                                                description="The metric returned by {}".format(
                                                                    self.name))
            else:
                return

        # Persist tracking object to output
        _logger_output.metric = metric_to.store()
