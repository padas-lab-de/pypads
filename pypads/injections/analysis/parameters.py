from typing import List, Type

from pydantic import HttpUrl, BaseModel

from pypads import logger
from pypads.app.env import InjectionLoggerEnv
from pypads.app.injections.base_logger import TrackedObject, LoggerCall
from pypads.app.injections.injection import InjectionLogger
from pypads.arguments import ontology_uri
from pypads.model.models import TrackedObjectModel, ContextModel, OutputModel, \
    ParameterMetaModel
from pypads.utils.util import dict_merge


class ParametersTO(TrackedObject):
    """
    Tracking object class for model hyperparameters.
    """

    class HyperParameterModel(TrackedObjectModel):
        uri: HttpUrl = f"{ontology_uri}ModelHyperparameter"

        context: ContextModel = ...
        hyperparameters: List[ParameterMetaModel] = []

    def __init__(self, *args, tracked_by: LoggerCall, **kwargs):
        super().__init__(*args, tracked_by=tracked_by, **kwargs)
        self.context = tracked_by._logging_env.call.call_id.context

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.HyperParameterModel

    def _persist_parameter(self, key, value, description=None, type=""):
        name = self.context.reference + "." + key
        description = description or "Hyperparameter {} of context {}".format(name, self.context)
        meta = ParameterMetaModel(name=name,
                                  description=description,
                                  type=type)
        self.hyperparameters.append(meta)
        self._store_param(value, meta)


# def persist_parameter(_pypads_env, key, value):
#     try:
#         # TODO broken reference
#         try_mlflow_log(mlflow.log_param,
#                        _pypads_env.call.call_id.context.container.__name__ + "." + key + ".txt",
#                        value)
#     except Exception as e:
#         logger.warning(
#             "Couldn't track parameter. " + str(e) + " Trying to track with another name.")
#         try_mlflow_log(mlflow.log_param,
#                        str(_pypads_env.call) + "." + key + ".txt", value)


class ParametersILF(InjectionLogger):
    """
    Function logging the hyperparameters of the current pipeline object.
    """
    name = "ParametersLogger"
    uri = f"{ontology_uri}hyperparameters-logger"

    class ParametersILFOutput(OutputModel):
        is_a: HttpUrl = f"{ontology_uri}ParametersILF-Output"
        hyperparameters: ParametersTO.get_model_cls() = ...

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.ParametersILFOutput

    def __post__(self, ctx, *args, _pypads_env: InjectionLoggerEnv, _logger_call, _logger_output, **kwargs):
        """
        Function logging the parameters of the current pipeline object function call.
        :param ctx:
        :param args:
        :param kwargs:
        :return:
        """
        hyper_params = ParametersTO(tracked_by=_logger_call)
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
                            description = parameter.get('description', None)
                            type = parameter.get('kind_of_value', "")
                            hyper_params._persist_parameter(key, value, description, type)
                        else:
                            logger.warning("Couldn't access parameter " + key + " on " + str(ctx.__class__))
            else:
                logger.warning("No parameters are defined on the mapping file for " + str(
                    ctx.__class__) + ". Trying to extract by other means...")
                for key, value in ctx.get_params().items():
                    hyper_params._persist_parameter(key, value)
        except Exception as e:
            logger.error("Couldn't extract parameters on " + str(_pypads_env) + " due to " + str(e))
            # TODO what to with keras etc? Or define multiple loggers.
        finally:
            hyper_params.store(_logger_output, "hyperparameters")
