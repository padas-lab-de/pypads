import os
from typing import List, Type

from pydantic import BaseModel, HttpUrl

from pypads.app.injections.base_logger import InjectionLoggerFunction, LoggerCall, LoggerTrackingObject
from pypads.model.models import ArtifactMetaModel, TrackingObjectModel
from pypads.utils.logging_util import WriteFormats


# TODO Literal for python 3.7 / 3.8?
class InputTO(LoggerTrackingObject):
    """
    Tracking object class for inputs of your tracked workflow.
    """
    class InputModel(TrackingObjectModel):
        uri: HttpUrl = "https://www.padre-lab.eu/onto/FunctionInput"

        class ParamModel(BaseModel):
            content_format: WriteFormats = WriteFormats.pickle
            name: str = ...
            value: str = ...  # path to the artifact containing the param
            type: str = ...

            class Config:
                orm_mode = True
                arbitrary_types_allowed = True

        input: List[ParamModel] = []

    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.InputModel

    def __init__(self, *args, call: LoggerCall, **kwargs):
        super().__init__(*args, original_call=call, **kwargs)

    def add_arg(self, name, value, format):
        self._add_param(name, value, format, 0)

    def add_kwarg(self, name, value, format):
        self._add_param(name, value, format, "kwarg")

    def _add_param(self, name, value, format, type):
        # TODO try to extract parameter documentation?
        index = len(self.input)
        path = os.path.join(self._base_path(), self._get_artifact_path(name))
        self.input.append(self.InputModel.ParamModel(content_format=format, name=name, value=path, type=type))
        self._store_artifact(value, ArtifactMetaModel(path=path,
                                                      description="Input to function with index {} and type {}".format(
                                                          index, type),
                                                      format=format))

    def _get_artifact_path(self, name):
        return os.path.join(self.call.original_call.to_folder(), "input", name)


class Input(InjectionLoggerFunction):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    name = "InputLogger"
    uri = "https://www.padre-lab.eu/onto/input-logger"

    def tracking_object_schemata(self):
        return [InputTO.InputModel.schema()]

    def __pre__(self, ctx, *args, _pypads_write_format=None, _logger_call: LoggerCall, _args, _kwargs, **kwargs):
        """
        :param ctx:
        :param args:
        :param _pypads_write_format:
        :param kwargs:
        :return:
        """

        inputs = InputTO(call=_logger_call)
        for i in range(len(_args)):
            arg = _args[i]
            inputs.add_arg(str(i), arg, format=_pypads_write_format)

        for (k, v) in _kwargs.items():
            inputs.add_kwarg(str(k), v, format=_pypads_write_format)


class OutputTO(LoggerTrackingObject):
    """
    Tracking object class for inputs of your tracked workflow.
    """

    def _path_name(self):
        return "inputs"

    class OutputModel(TrackingObjectModel):
        uri: HttpUrl = "https://www.padre-lab.eu/onto/FunctionOutput"

        content_format: WriteFormats = WriteFormats.pickle
        output: str = ...  # Path to the output holding file

        class Config:
            orm_mode = True
            arbitrary_types_allowed = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.OutputModel

    def __init__(self, value, format, *args, call: LoggerCall, **kwargs):
        super().__init__(*args, output="", content_format=format, original_call=call,
                         **kwargs)
        path = os.path.join(self._base_path(), self.call.original_call.to_folder(), "output")
        self.output = path
        self._store_artifact(value, ArtifactMetaModel(path=path,
                                                      description="Output of function call {}".format(
                                                          self.call.original_call),
                                                      format=format))


class Output(InjectionLoggerFunction):
    """
    Function logging the output of the current pipeline object function call.
    """

    def tracking_object_schemata(self):
        return [OutputTO.OutputModel.schema()]

    name = "OutputLogger"
    uri = "https://www.padre-lab.eu/onto/output-logger"

    def __post__(self, ctx, *args, _pypads_write_format=WriteFormats.pickle, _logger_call, _pypads_result, **kwargs):
        """
        :param ctx:
        :param args:
        :param _pypads_write_format:
        :param kwargs:
        :return:
        """
        OutputTO(_pypads_result, _pypads_write_format, call=_logger_call)
