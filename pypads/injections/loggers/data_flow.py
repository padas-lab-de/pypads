from typing import List, Type

from pydantic import BaseModel

from pypads.app.injections.injection import InjectionLogger
from pypads.app.injections.tracked_object import LoggerCall, TrackedObject, LoggerOutput
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.logging_util import FileFormats


class InputTO(TrackedObject):
    """
    Tracking object class for inputs of your tracked workflow.
    """

    class InputModel(TrackedObjectModel):
        category: str = "FunctionInput"
        description = "The input to the tracked function."
        inputs: List[str] = []

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.InputModel

    def add_arg(self, name, value, format):
        self._add_param(name, value, format, "argument")

    def add_kwarg(self, name, value, format):
        self._add_param(name, value, format, "keyword-argument")

    def _add_param(self, name, value, format, type):
        description = "Input to function with index {} and type {}".format(len(self.inputs), type)
        self.inputs.append(self.store_artifact(name, value, write_format=format, description=description))


class InputILF(InjectionLogger):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    name = "Generic-InputLogger"
    category = "InputLogger"

    class InputILFOutput(OutputModel):
        category: str = "InputILF-Output"
        FunctionInput: str = ...

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls):
        return cls.InputILFOutput

    def __pre__(self, ctx, *args, _pypads_write_format=None, _logger_call: LoggerCall, _logger_output, _args, _kwargs,
                **kwargs):
        """
        :param ctx:
        :param args:
        :param _pypads_write_format:
        :param kwargs:
        :return:
        """

        inputs = InputTO(parent=_logger_output)
        for i in range(len(_args)):
            arg = _args[i]
            inputs.add_arg(str(i), arg, format=_pypads_write_format)

        for (k, v) in _kwargs.items():
            inputs.add_kwarg(str(k), v, format=_pypads_write_format)
        inputs.store(_logger_output, key="FunctionInput")


class OutputTO(TrackedObject):
    """
    Tracking object class for inputs of your tracked workflow.
    """

    def _path_name(self):
        return "inputs"

    class OutputModel(TrackedObjectModel):
        category: str = "FunctionOutput"
        description = "The output of the tracked function."

        output: str = ...  # Path to the output holding file

        class Config:
            orm_mode = True
            arbitrary_types_allowed = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.OutputModel

    def __init__(self, value, format, *args, parent: LoggerOutput, **kwargs):
        super().__init__(*args, content_format=format, parent=parent, **kwargs)
        # self.output = self.store_artifact(self.get_artifact_path(), value, write_format=format,
        #                                   description="Output of function call {}".format(
        #                                       self.producer.original_call))


class OutputILF(InjectionLogger):
    """
    Function logging the output of the current pipeline object function call.
    """

    name = "GenericOutputLogger"
    category = "OutputLogger"

    class OutputILFOutput(OutputModel):
        category: str = "OutputILF-Output"
        FunctionOutput: str = ...

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls):
        return cls.OutputILFOutput

    def __post__(self, ctx, *args, _pypads_write_format=FileFormats.pickle, _logger_call, _pypads_result,
                 _logger_output, **kwargs):
        """
        :param ctx:
        :param args:
        :param _pypads_write_format:
        :param kwargs:
        :return:
        """
        output = OutputTO(_pypads_result, format=_pypads_write_format, parent=_logger_output)
        _logger_output["FunctionOutput"] = output.store()
