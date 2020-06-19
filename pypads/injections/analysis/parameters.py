import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads import logger
from pypads.app.injections.base_logger import LoggingFunction
from pypads.injections.analysis.call_tracker import LoggingEnv


def persist_parameter(_pypads_env, key, value):
    try:
        # TODO broken reference
        try_mlflow_log(mlflow.log_param,
                       _pypads_env.call.call_id.context.container.__name__ + "." + key + ".txt",
                       value)
    except Exception as e:
        logger.warning(
            "Couldn't track parameter. " + str(e) + " Trying to track with another name.")
        try_mlflow_log(mlflow.log_param,
                       str(_pypads_env.call) + "." + key + ".txt", value)


class Parameters(LoggingFunction):

    def __pre__(self, ctx, *args, _pypads_env, **kwargs):
        pass

    def __post__(self, ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        """
        Function logging the parameters of the current pipeline object function call.
        :param ctx:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            if 'hyper_parameters' in _pypads_env.mapping.values['data']:
                for type, parameters in _pypads_env.mapping.values['data']['hyper_parameters'].items():
                    for parameter in parameters:
                        key = parameter["name"]
                        if "path" in parameter and hasattr(ctx, parameter["path"]):
                            value = getattr(ctx, parameter["path"])
                            persist_parameter(_pypads_env, key, value)
                        else:
                            logger.warning("Couldn't access parameter " + key + " on " + str(ctx.__class__))
            else:
                logger.warning("No parameters are defined on the mapping file for " + str(
                    ctx.__class__) + ". Trying to extract by other means...")
                for key, value in ctx.get_params():
                    persist_parameter(_pypads_env, key, value)
        except Exception as e:
            logger.error(e)
