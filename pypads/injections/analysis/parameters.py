from typing import List, Type

from pydantic import HttpUrl, BaseModel

from pypads import logger
from pypads.app.env import InjectionLoggerEnv
from pypads.app.injections.base_logger import TrackedObject, LoggerCall, LoggerOutput
from pypads.app.injections.injection import InjectionLogger
from pypads.arguments import ontology_uri
from pypads.model.logger_call import ContextModel
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.logging_util import _to_param_meta_name
from pypads.utils.util import dict_merge


class ParametersTO(TrackedObject):
    """
    Tracking object class for model hyperparameters.
    """

    class HyperParameterModel(TrackedObjectModel):
        is_a: HttpUrl = f"{ontology_uri}ModelHyperparameter"

        ml_model: ContextModel = ...
        hyperparameters: List[str] = []

    def __init__(self, *args, part_of: LoggerOutput, **kwargs):
        super().__init__(*args, part_of=part_of, **kwargs)
        self.ml_model = self._tracked_by._logging_env.call.call_id.context

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.HyperParameterModel

    def _persist_parameter(self, key, value, param_type=None, description=None):
        name = self.ml_model.reference + "." + key
        description = description or "Hyperparameter {} of context {}".format(name, self.ml_model)
        self.hyperparameters.append(_to_param_meta_name(name))
        self.store_param(name, value, param_type=param_type, description=description)


class ParametersILF(InjectionLogger):
    """
    Function logging the hyperparameters of the current pipeline object.
    """
    name = "ParametersLogger"
    uri = f"{ontology_uri}hyperparameters-logger"

    class ParametersILFOutput(OutputModel):
        is_a: HttpUrl = f"{ontology_uri}ParametersILF-Output"
        hyperparameters: str = ...

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
        hyper_params = ParametersTO(part_of=_logger_output)
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
                            hyper_params._persist_parameter(key, value, type, description)
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
