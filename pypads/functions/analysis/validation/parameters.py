from logging import warning

import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads.functions.analysis.call_tracker import LoggingEnv
from pypads.functions.analysis.validation.generic_visitor import default_visitor
from pypads.functions.loggers.base_logger import LoggingFunction


class Parameter(LoggingFunction):

    def __post__(self, ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        """
        Function logging the parameters of the current pipeline object function call.
        :param ctx:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            # prevent wrapped_class from becoming unwrapped
            visitor = default_visitor(ctx)

            for k, v in visitor[0]["steps"][0]["hyper_parameters"]["model_parameters"].items():
                try:
                    try_mlflow_log(mlflow.log_param, _pypads_env.mapping.reference + "." + k + ".txt", v)
                except Exception as e:
                    warning("Couldn't track parameter. " + str(e) + " Trying to track with another name.")
                    try_mlflow_log(mlflow.log_param,
                                   str(_pypads_env.call) + "." + k + ".txt", v)

        except Exception as e:
            warning("Couldn't use visitor for parameter extraction. " + str(e) + " Omit logging for now.")
