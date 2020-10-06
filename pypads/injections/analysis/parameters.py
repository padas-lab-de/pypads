import uuid
from typing import List, Type, Union

from pydantic import BaseModel

from pypads import logger
from pypads.app.env import InjectionLoggerEnv
from pypads.app.injections.injection import InjectionLogger
from pypads.app.injections.tracked_object import TrackedObject
from pypads.model.logger_call import ContextModel
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.util import dict_merge


class ParametersTO(TrackedObject):
    """
    Tracking object class for model hyperparameters.
    """

    class HyperParameterModel(TrackedObjectModel):
        category: str = "ModelHyperparameter"
        description = "The parameters of the experiment."
        ml_model: ContextModel = ...
        hyperparameters: List[Union[uuid.UUID, str]] = []

    def __init__(self, *args, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        super().__init__(*args, parent=parent, **kwargs)
        self.ml_model = self.producer.original_call.call_id.context

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.HyperParameterModel

    def _persist_parameter(self, key, value, param_type=None, description=None):
        name = self.ml_model.reference + "." + key
        description = description or "Hyperparameter {} of context {}".format(name, self.ml_model)
        self.hyperparameters.append(self.store_param(name, value, param_type=param_type, description=description))


class ParametersILF(InjectionLogger):
    """
    Function logging the hyperparameters of the current pipeline object.
    """
    name = "Generic Hyperparameter Logger"
    category: str = "HyperparameterLogger"

    class ParametersILFOutput(OutputModel):
        category: str = "ParametersILF-Output"
        hyperparameters: Union[uuid.UUID, str] = ...

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
        hyper_params = ParametersTO(parent=_logger_output)
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
            _logger_output.hyperparameters = hyper_params.store()
