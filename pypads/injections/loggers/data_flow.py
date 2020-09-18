import os
from typing import List, Type

from pydantic import BaseModel, HttpUrl

from pypads.app.injections.base_logger import LoggerCall, TrackedObject
from pypads.app.injections.injection import InjectionLogger
from pypads.arguments import ontology_uri
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.logging_util import FileFormats


class InputTO(TrackedObject):
    """
    Tracking object class for inputs of your tracked workflow.
    """

    class InputModel(TrackedObjectModel):
        uri: HttpUrl = f"{ontology_uri}FunctionInput"

        inputs: List[str] = []

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.InputModel

    def add_arg(self, name, value, format):
        self._add_param(name, value, format, "argument")

    def add_kwarg(self, name, value, format):
        self._add_param(name, value, format, "keyword-argument")

    def _add_param(self, name, value, format, type):
        path = self.get_artifact_path(name)
        description = "Input to function with index {} and type {}".format(len(self.inputs), type)
        self.inputs.append(self.store_artifact(path, value, write_format=format, description=description))

    def get_artifact_path(self, name):
        return os.path.join(self.get_dir(), "input", name)


class InputILF(InjectionLogger):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    name = "InputLogger"
    uri = f"{ontology_uri}input-logger"

    class InputILFOutput(OutputModel):
        is_a: HttpUrl = f"{ontology_uri}InputILF-Output"
        FunctionInput: InputTO.get_model_cls() = ...

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

        inputs = InputTO(tracked_by=_logger_call)
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
        uri: HttpUrl = f"{ontology_uri}FunctionOutput"

        output: str = ...  # Path to the output holding file

        class Config:
            orm_mode = True
            arbitrary_types_allowed = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.OutputModel

    def __init__(self, value, format, *args, tracked_by: LoggerCall, **kwargs):
        super().__init__(*args, content_format=format, tracked_by=tracked_by, **kwargs)
        self.output = self.store_artifact(self.get_artifact_path(), value, write_format=format,
                                          description="Output of function call {}".format(
                                              self._tracked_by.original_call))

    def get_artifact_path(self, name="output"):
        return super().get_artifact_path(name)


class OutputILF(InjectionLogger):
    """
    Function logging the output of the current pipeline object function call.
    """

    name = "OutputLogger"
    uri = f"{ontology_uri}output-logger"

    class OutputILFOutput(OutputModel):
        is_a: HttpUrl = f"{ontology_uri}OutputILF-Output"
        FunctionOutput: OutputTO.get_model_cls() = ...

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
        output = OutputTO(_pypads_result, format=_pypads_write_format, tracked_by=_logger_call)
        output.store(_logger_output, key="FunctionOutput")
