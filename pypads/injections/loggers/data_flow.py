import os

from pypads.app.injections.base_logger import LoggingFunction
from pypads.app.tracking.base import TrackingObject
from pypads.injections.analysis.call_tracker import LoggingEnv
from pypads.utils.logging_util import WriteFormats, try_write_artifact


class DataFlow(TrackingObject):
    """
    Tracking object class for inputs and outputs of your tracked workflow.
    """
    PATH = "DataFlow"
    CONTENT_FORMAT = WriteFormats.pickle

    def write_content(self, name, obj, prefix=None, write_format=None):
        if prefix:
            name = '.'.join([prefix, name])
        _entry = {'name': name, 'obj': obj}
        if write_format:
            _entry.update({'format': write_format})
        self.content.append(_entry)


class Input(LoggingFunction):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    TRACKINGOBJECT = DataFlow

    def __pre__(self, ctx, *args, _pypads_write_format=None, _pypads_env: LoggingEnv, **kwargs):
        """
        :param ctx:
        :param args:
        :param _pypads_write_format:
        :param kwargs:
        :return:
        """
        self.tracking_object.add_suffix('Inputs')
        for i in range(len(args)):
            arg = args[i]
            self.tracking_object.write_content('Arg', str(i), arg, write_format=_pypads_write_format)
            # arg = args[i]
            # name = os.path.join(_pypads_env.call.to_folder(),
            #                     "args",
            #                     str(i) + "_" + str(id(_pypads_env.callback)))
            # try_write_artifact(name, arg, _pypads_write_format)

        for (k, v) in kwargs.items():
            self.tracking_object.write_content('Kwarg', str(k), v, write_format=_pypads_write_format)
            # name = os.path.join(_pypads_env.call.to_folder(),
            #                     "kwargs",
            #                     str(k) + "_" + str(id(_pypads_env.callback)))
            # try_write_artifact(name, v, _pypads_write_format)


class Output(LoggingFunction):
    """
    Function logging the output of the current pipeline object function call.
    """

    TRACKINGOBJECT = DataFlow

    def __post__(self, ctx, *args, _pypads_write_format=WriteFormats.pickle, _pypads_env, _pypads_result, **kwargs):
        """
        :param ctx:
        :param args:
        :param _pypads_write_format:
        :param kwargs:
        :return:
        """
        self.tracking_object.add_suffix('Outputs')
        self.tracking_object.write_content('Returned_value', _pypads_result, write_format=_pypads_write_format)
        # name = os.path.join(_pypads_env.call.to_folder(),
        #                     "returns",
        #                     str(id(_pypads_env.callback)))
        # try_write_artifact(name, kwargs["_pypads_result"], _pypads_write_format)
