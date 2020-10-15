import uuid
from typing import List, Type, Union

from pydantic import BaseModel

from pypads import logger
from pypads.app.env import InjectionLoggerEnv
from pypads.app.injections.injection import InjectionLogger
from pypads.app.injections.tracked_object import TrackedObject, LoggerOutput
from pypads.model.logger_call import ContextModel
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.logging_util import data_str, data_path


class ParametersILFOutput(OutputModel):
    """
    Output of the logger. An output can reference multiple Tracked Objects or Values directly. In this case a own
    tracked object doesn't give a lot of benefit but enforcing a description a name and a category and could be omitted.
    """
    category: str = "ParametersILF-Output"
    hyper_parameter_to: Union[uuid.UUID, str] = ...


class ParametersTO(TrackedObject):
    """
    Tracking object class for model hyper parameters.
    """

    class HyperParameterModel(TrackedObjectModel):
        category: str = "ModelHyperParameter"
        description = "The parameters of the experiment."
        ml_model: ContextModel = ...
        estimator: str = ...
        hyper_parameters: List[Union[uuid.UUID, str]] = []

    def __init__(self, *args, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        super().__init__(*args, parent=parent, **kwargs)
        self.ml_model = self.producer.original_call.call_id.context

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.HyperParameterModel

    def persist_parameter(self: Union['ParametersTO', HyperParameterModel], key, value, param_type=None,
                          description=None, additional_data=None):
        """
        Persist a new parameter to the tracking object.
        :param key: Name of the parameter
        :param value: Value of the parameter. This has to be convert-able to string
        :param param_type: Type of the parameter. This should store the real type of the parameter. It could be used
        to load the data in the right format from the stored string.
        :param description: A description of the parameter to be stored.
        :param additional_data: Additional data to store about the parameter.
        :return:
        """
        name = self.ml_model.reference + "." + key
        description = description or "Parameter {} of context {}".format(name, self.ml_model)
        self.hyper_parameters.append(self.store_param(name, value, param_type=param_type, description=description,
                                                      additional_data=additional_data))


class ParametersILF(InjectionLogger):
    """
    Function logging the hyper parameters of the current pipeline object. This stores parameters as pypads parameters.
    Mapping files should give data in the format of:

        Hook:
            Hook this logger to function calls on which an estimator parameter setting should be extracted. For sklearn
            this is the fit, fit_predict etc. function. Generally one could log parameters on initialisation of an
            estimator too but this would't be able to track changes to the parameter settings done in between inti
            and fitting.
        Mapping_File:
            data:
                estimator:
                    parameters:
                        model_parameters:
                        - name: split_quality
                          kind_of_value: "{'gini', 'entropy'}"
                          optional: 'True'
                          description: The function to measure the quality of a split.
                          default_value: "'gini'"
                          path: criterion
                          ...
                      optimisation_parameters:
                        - name: presort
                          kind_of_value: "{boolean, 'auto'}"
                          optional: 'True'
                          description: Whether to presort the data to speed up the finding of best splits
                            in fitting.
                          default_value: "'auto'"
                          path: presort
                      execution_parameters: []
    """

    name = "Parameter Logger"
    category: str = "ParameterLogger"

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return ParametersILFOutput

    def __post__(self, ctx, *args, _pypads_env: InjectionLoggerEnv, _logger_call,
                 _logger_output: Union['ParametersILFOutput', LoggerOutput], **kwargs):
        """
        Function logging the parameters of the current pipeline object function call.
        """
        hyper_params = ParametersTO(parent=_logger_output)

        mapping_data = _pypads_env.data

        if 'estimator' not in mapping_data or 'parameters' not in mapping_data['estimator']:
            logger.warning("No parameters are defined on the mapping file for " + str(
                ctx.__class__) + ". Trying to log parameters without schema definition programmatically.")
            for key, value in ctx.get_params().items():
                hyper_params.persist_parameter(key, value)
            hyper_params.estimator = ctx.__class__.__name__
        else:
            hyper_params.estimator = data_str(mapping_data, "estimator", "@schema", "rdfs:label",
                                              default=ctx.__class__.__name__)

            for parameter_type, parameters in data_path(mapping_data, "estimator", "parameter", default={}).items():
                for parameter in parameters:
                    parameter = data_path(parameter, "@schema")
                    key = data_path(parameter, "padre:value_type")
                    if key is not None and hasattr(ctx, key):
                        value = getattr(ctx, key)
                        description = data_path(parameter, "rdfs:description",
                                                default="No description in mapping file.")
                        parameter_type = data_path(parameter, "padre:value_type", default=str(type(value)))
                        hyper_params.persist_parameter(key, value, parameter_type, description,
                                                       additional_data=parameter)
                    else:
                        logger.warning(
                            f"Couldn't access im mapping file defined parameter {parameter} on {ctx.__class__}")

        _logger_output.hyper_parameter_to = hyper_params.store()
