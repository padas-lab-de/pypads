from logging import warning, info

import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads.functions.loggers.base_logger import LoggingFunction
from pypads.logging_util import try_write_artifact, WriteFormats


class Metric(LoggingFunction):
    """
    Function logging the wrapped metric function
    """

    def __post__(self, ctx, *args, _pypads_artifact_fallback=False, _pypads_env, _pypads_result, **kwargs):
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
                try_mlflow_log(mlflow.log_metric, _pypads_env.call.call_id.context.container.__name__ + ".txt", result)
            else:
                warning("Mlflow metrics have to be doubles. Could log the return value of type '" + str(
                    type(
                        result)) + "' of '" + _pypads_env.call.call_id.context.container.__name__ + _pypads_env.call.call_id.wrappee.__name__ + "' as artifact instead.")

                # TODO search callstack for already logged functions and ignore?
                if _pypads_artifact_fallback:
                    info("Logging result if '" + _pypads_env.call.call_id.context.container.__name__ + "' as artifact.")
                    try_write_artifact(_pypads_env.call.call_id.context.container.__name__, str(result),
                                       WriteFormats.text)
