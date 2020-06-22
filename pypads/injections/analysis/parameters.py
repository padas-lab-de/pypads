import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads import logger
from pypads.app.injections.base_logger import LoggingFunction
from pypads.injections.analysis.call_tracker import LoggingEnv
from pypads.utils.util import dict_merge


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

    def __post__(self, ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        """
        Function logging the parameters of the current pipeline object function call.
        :param ctx:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            data = {}
            for mm in _pypads_env.mappings:
                if "data" in mm.mapping.values and 'hyper_parameters' in mm.mapping.values['data']:
                    data = dict_merge(data, mm.mapping.values['data']['hyper_parameters'])
            if len(data) > 0:
                for type, parameters in data.items():
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
                for key, value in ctx.get_params().items():
                    persist_parameter(_pypads_env, key, value)
        except Exception as e:
            logger.error("Couldn't extract parameters on " + str(_pypads_env) + " due to " + str(e))
