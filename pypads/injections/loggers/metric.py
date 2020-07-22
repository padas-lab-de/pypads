import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads import logger
from pypads.app.injections.injection_loggers import InjectionLoggerFunction
from pypads.utils.logging_util import try_write_artifact, WriteFormats


class Metric(InjectionLoggerFunction):
    """
    Function logging the wrapped metric function
    """

    def __post__(self, ctx, *args, _pypads_artifact_fallback=False, _logger_call, _pypads_result, **kwargs):
        """

        :param ctx:
        :param args:
        :param _pypads_artifact_fallback: Write to artifact if metric can not be logged as an double value into mlflow
        :param _pypads_result:
        :param kwargs:
        :return:
        """
        result = _pypads_result

        if result is not None:
            if isinstance(result, float):
                try_mlflow_log(mlflow.log_metric,
                               _logger_call.original_call.call_id.context.container.__name__ + "." + _logger_call.original_call.call_id.wrappee.__name__ + ".txt",
                               result, step=_logger_call.original_call.call_id.call_number)
            else:
                logger.warning("Mlflow metrics have to be doubles. Could log the return value of type '" + str(
                    type(
                        result)) + "' of '" + _logger_call.original_call.call_id.context.container.__name__ + "." + _logger_call.original_call.call_id.wrappee.__name__ + "' as artifact instead.")

                # TODO search callstack for already logged functions and ignore?
                if _pypads_artifact_fallback:
                    logger.info(
                        "Logging result if '" + _logger_call.original_call.call_id.context.container.__name__ + "' as artifact.")
                    try_write_artifact(_logger_call.original_call.call_id.context.container.__name__, str(result),
                                       WriteFormats.text)
