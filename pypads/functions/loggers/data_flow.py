import os

from pypads.analysis.call_objects import get_current_call_folder
from pypads.functions.loggers.base_logger import LoggingFunction
from pypads.logging_util import WriteFormats, try_write_artifact


class Input(LoggingFunction):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.pickle, **kwargs):
        """
        :param ctx:
        :param args:
        :param _pypads_write_format:
        :param kwargs:
        :return:
        """
        for i in range(len(args)):
            arg = args[i]
            name = os.path.join(get_current_call_folder(self, kwargs["_pypads_context"], kwargs["_pypads_wrappe"]),
                                "args",
                                str(i) + "_" + str(id(kwargs["_pypads_callback"])))
            try_write_artifact(name, arg, _pypads_write_format)

        for (k, v) in kwargs.items():
            name = os.path.join(get_current_call_folder(self, kwargs["_pypads_context"], kwargs["_pypads_wrappe"]),
                                "kwargs",
                                str(k) + "_" + str(id(kwargs["_pypads_callback"])))
            try_write_artifact(name, v, _pypads_write_format)


class Output(LoggingFunction):
    """
    Function logging the output of the current pipeline object function call.
    """

    def __post__(self, ctx, *args, _pypads_write_format=WriteFormats.pickle, **kwargs):
        """
        :param ctx:
        :param args:
        :param _pypads_write_format:
        :param kwargs:
        :return:
        """
        name = os.path.join(get_current_call_folder(self, kwargs["_pypads_context"], kwargs["_pypads_wrappe"]),
                            "returns",
                            str(id(kwargs["_pypads_callback"])))
        try_write_artifact(name, kwargs["_pypads_result"], _pypads_write_format)
