from _py_abc import ABCMeta
from logging import exception

import mlflow

from pypads.analysis.call_objects import get_current_call_str


# noinspection PyBroadException
class LoggingFunction(object):
    __metaclass__ = ABCMeta
    """
    This class should be used to define new loggers
    """

    def __init__(self, **static_parameters):
        self._static_parameters = static_parameters

    def __pre__(self, ctx, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
        """
        The function to be called before executing the log anchor
        :param ctx:
        :param args:
        :param _pypads_wrappe:
        :param _pypads_context:
        :param _pypads_mapped_by:
        :param _pypads_callback:
        :param kwargs:
        :return:
        """
        pass

    # noinspection PyMethodMayBeStatic
    def _handle_failure(self, ctx, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
                        _pypads_hook_params, _pypads_error, **kwargs):
        try:
            mlflow.set_tag("pypads_failure", str(_pypads_error))
            exception(
                "Tracking failed for " + get_current_call_str(ctx, _pypads_context, _pypads_wrappe) + " with: " + str(
                    _pypads_error))
        except Exception:
            exception("Tracking failed for " + str(_pypads_wrappe) + " with: " + str(_pypads_error))

    def __call__(self, ctx, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
                 _pypads_hook_params, **kwargs):
        """
        The call of the loggingFunction
        :param ctx:
        :param args:
        :param _pypads_wrappe:
        :param _pypads_context:
        :param _pypads_mapped_by:
        :param _pypads_callback:
        :param kwargs:
        :return:
        """
        # Add the static parameters to our passed parameters
        _pypads_hook_params = {**self._static_parameters, **_pypads_hook_params}

        # Call function to be executed before the tracked function
        try:
            self.__pre__(ctx, *args, _pypads_wrappe=_pypads_wrappe, _pypads_context=_pypads_context,
                         _pypads_mapped_by=_pypads_mapped_by, _pypads_callback=_pypads_callback,
                         **{**_pypads_hook_params, **kwargs})
        except Exception as e:
            self._handle_failure(e)

        # Call the output producing code
        out = self.call_wrapped(ctx, *args, _pypads_wrappe=_pypads_wrappe, _pypads_context=_pypads_context,
                                _pypads_mapped_by=_pypads_mapped_by, _pypads_callback=_pypads_callback,
                                **{**_pypads_hook_params, **kwargs})

        # Call function to be executed after the tracked function
        try:
            self.__post__(ctx, *args, _pypads_wrappe=_pypads_wrappe, _pypads_context=_pypads_context,
                          _pypads_mapped_by=_pypads_mapped_by, _pypads_callback=_pypads_callback, _pypads_result=out,
                          **{**_pypads_hook_params, **kwargs})
        except Exception as e:
            self._handle_failure(ctx, *args, _pypads_wrappe=_pypads_wrappe, _pypads_context=_pypads_context,
                                 _pypads_mapped_by=_pypads_mapped_by, _pypads_callback=_pypads_callback,
                                 _pypads_error=e,
                                 **{**_pypads_hook_params, **kwargs})
        return out

    # noinspection PyMethodMayBeStatic
    def call_wrapped(self, ctx, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
                     _pypads_hook_params, **kwargs):
        """
        The real call of the wrapped function. Be carefull when you change this.
        Exceptions here will not be catched automatically and might break your workflow.
        :param ctx:
        :param args:
        :param _pypads_wrappe:
        :param _pypads_context:
        :param _pypads_mapped_by:
        :param _pypads_callback:
        :param _pypads_hook_params:
        :param kwargs:
        :return:
        """
        return _pypads_callback(*args, **kwargs)

    def __post__(self, ctx, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, _pypads_result,
                 **kwargs):
        """
        The function to be called after executing the log anchor
        :param ctx:
        :param args:
        :param _pypads_wrappe:
        :param _pypads_context:
        :param _pypads_mapped_by:
        :param _pypads_callback:
        :param kwargs:
        :return:
        """
        pass
