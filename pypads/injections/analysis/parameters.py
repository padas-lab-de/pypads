from typing import List, Type, Union

from pydantic import BaseModel

from pypads import logger
from pypads.app.env import InjectionLoggerEnv
from pypads.app.injections.injection import InjectionLogger
from pypads.app.injections.tracked_object import TrackedObject, LoggerOutput
from pypads.model.logger_call import ContextModel
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.model.models import IdReference
from pypads.utils.logging_util import data_str, data_path, add_data


class FunctionParametersTO(TrackedObject):
    """
    Tracking object class for model hyper parameters.
    """

    class FunctionParametersModel(TrackedObjectModel):
        type: str = "ModelHyperParameter"
        description = "The parameters of the experiment."
        estimator: str = ...
        ml_model: ContextModel = ...
        hyper_parameters: List[IdReference] = []

    def __init__(self, *args, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        super().__init__(*args, parent=parent, **kwargs)
        self.ml_model = self.producer.original_call.call_id.context

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.FunctionParametersModel

    def persist_parameter(self: Union['FunctionParametersTO', FunctionParametersModel], key, value, param_type=None,
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
        description = description or "Parameter named {} of context {}".format(key, self.ml_model)
        self.hyper_parameters.append(self.store_param(key, value, param_type=param_type, description=description,
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
        '@json-ld':
        - estimator.@schema
        - estimator.alogorithm.@schema
        - parameters.model_parameters.algorithm.@schema
        estimator:
          '@schema':
            '@id': padre:sklearn.tree.tree.DecisionTreeClassifier
            '@type': padre:Estimator
            padre:documentation: TBD
            padre:implements: padre:DecisionTreeClassifier
            rdfs:description: ''
            rdfs:label: decision tree classifier
          algorithm:
            '@schema':
              '@id': padre:DecisionTreeClassifier
              '@type': padre:Algorithm
              padre:documentation: TBD
              rdfs:description: ''
              rdfs:label: decision tree classifier
          parameters:
            optimisation_parameters: []
            execution_parameters: []
            model_parameters:
            - '@schema':
                '@id': padre:sklearn.tree.tree.DecisionTreeClassifier/split_quality
                '@type': padre:ModelParameters
                padre:configures: padre:sklearn.tree.tree.DecisionTreeClassifier/split_quality
                padre:implements: padre:DecisionTreeClassifier/split_quality
                padre:optional: 'True'
                padre:path: criterion
                padre:value_default: '''gini'''
                padre:value_type: '{''gini'', ''entropy''}'
                rdfs:description: The function to measure the quality of a split.
                rdfs:label: split_quality
    """

    name = "Parameter Logger"
    type: str = "ParameterLogger"

    class ParametersILFOutput(OutputModel):
        """
        Output of the logger. An output can reference multiple Tracked Objects or Values directly. In this case a own
        tracked object doesn't give a lot of benefit but enforcing a description a name and a category and could be omitted.
        """
        type: str = "ParametersILF-Output"
        hyper_parameter_to: IdReference = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.ParametersILFOutput

    def __post__(self, ctx, *args, _pypads_env: InjectionLoggerEnv, _logger_call,
                 _logger_output: Union['ParametersILFOutput', LoggerOutput], **kwargs):
        """
        Function logging the parameters of the current pipeline object function call.
        """

        mapping_data = _pypads_env.data

        # Get the estimator name
        estimator = data_str(mapping_data, "estimator", "@schema", "rdfs:label",
                             default=ctx.__class__.__name__)

        hyper_params = FunctionParametersTO(estimator=estimator,
                                            description=f"The parameters of estimator {estimator} with {ctx}.",
                                            parent=_logger_output)

        # List of parameters to extract. Either provided by a mapping file or by get_params function or by _kwargs
        relevant_parameters = []

        if data_path(_pypads_env.data, "estimator", "parameters",
                     warning="No parameters are defined on the mapping file for " + str(
                         ctx.__class__) + ". Trying to log parameters without schema definition programmatically."):
            relevant_parameters = []
            for parameter_type, parameters in data_path(mapping_data, "estimator", "parameters", default={}).items():
                for parameter in parameters:
                    parameter = data_path(parameter, "@schema")
                    key = data_path(parameter, "padre:path")
                    name = data_path(parameter, "rdfs:label")

                    param_dict = {"name": name,
                                  "description": data_path(parameter, "rdfs:comment"),
                                  "parameter_type": data_path(parameter, "padre:value_type")}

                    if hasattr(ctx, key):
                        value = getattr(ctx, key)
                    else:
                        _kwargs = getattr(kwargs, "_kwargs")
                        if hasattr(_kwargs, key):
                            value = getattr(_kwargs, key)
                        else:
                            logger.warning(f"Couldn't extract value of in schema defined parameter {parameter}.")
                            continue
                    param_dict["value"] = value
                    add_data(mapping_data, "type", value=data_path(parameter, "@id"))
                    relevant_parameters.append(param_dict)

        else:
            get_params = getattr(ctx, "get_params", None)
            if callable(get_params):

                # Extracting via get_params (valid for sklearn)
                relevant_parameters = [{"name": k, "value": v} for k, v in ctx.get_params().items()]
            else:

                # Trying to get at least the named arguments
                relevant_parameters = [{"name": k, "value": v} for k, v in kwargs["_kwargs"].items()]

        for i, param in enumerate(relevant_parameters):
            name = data_path(param, "name", default="UnknownParameter" + str(i))
            description = data_path(param, "description")
            value = data_path(param, "value")
            parameter_type = data_path(param, "parameter_type", default=str(type(value)))

            try:
                from pypads.app.pypads import get_current_pads
                call_number = get_current_pads().call_tracker.call_number(_pypads_env.call.call_id)
                hyper_params.persist_parameter(".".join([estimator, str(call_number), name]), str(value),
                                               param_type=parameter_type,
                                               description=description,
                                               additional_data=mapping_data)
            except Exception as e:
                logger.error(f"Couldn't log parameter {estimator + '.' + name} with value {value}")

        _logger_output.hyper_parameter_to = hyper_params.store()
