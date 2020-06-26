from pypads.app.injections.base_logger import LoggingFunction
from pypads.app.tracking.base import LoggerTrackingObject
from pypads.injections.analysis.call_tracker import LoggingEnv
from pypads.utils.logging_util import WriteFormats, add_to_store_object


class DataFlow(LoggerTrackingObject):
    """
    Tracking object class for inputs and outputs of your tracked workflow.
    """
    PATH = "DataFlow"
    CONTENT_FORMAT = WriteFormats.pickle

    def write_data(self, name, obj, path_prefix=None, data_format=None):
        if path_prefix:
            name = '.'.join([path_prefix, name])
        _entry = {"name": self.to_path(name), "object": obj, "format": data_format or self.CONTENT_FORMAT}
        self.data.append(_entry)


class Input(LoggingFunction):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    def __pre__(self, ctx, *args, _pypads_write_format=None, _pypads_env: LoggingEnv, _args, _kwargs, **kwargs):
        """
        :param ctx:
        :param args:
        :param _pypads_write_format:
        :param kwargs:
        :return:
        """
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        input_flow = pads.tracking_object_factory(ctx, source=self, _pypads_env=_pypads_env, object_class=DataFlow)
        input_flow.set_suffix('Inputs')
        for i in range(len(_args)):
            arg = _args[i]
            input_flow.write_data(str(i), arg, path_prefix='Arg', data_format=_pypads_write_format)

        for (k, v) in _kwargs.items():
            input_flow.write_data(str(k), v, path_prefix='Kwarg', data_format=_pypads_write_format)

        add_to_store_object(self, input_flow, store=True)


class Output(LoggingFunction):
    """
    Function logging the output of the current pipeline object function call.
    """

    def __post__(self, ctx, *args, _pypads_write_format=WriteFormats.pickle, _pypads_env, _pypads_result, **kwargs):
        """
        :param ctx:
        :param args:
        :param _pypads_write_format:
        :param kwargs:
        :return:
        """
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        output_flow = pads.tracking_object_factory(ctx, source=self, _pypads_env=_pypads_env, object_class=DataFlow)
        output_flow.set_suffix('Outputs')
        output_flow.write_data('Returned_value', _pypads_result,
                               data_format=_pypads_write_format)

        add_to_store_object(self, output_flow, store=True)
