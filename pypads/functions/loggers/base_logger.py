from _py_abc import ABCMeta
from logging import exception, warning, error

import mlflow

from pypads.functions.analysis.call_tracker import LoggingEnv
from pypads.functions.analysis.time_keeper import timed, add_run_time, TimingDefined
from pypads.util import is_package_available


class MissingDependencyError(Exception):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DependencyMixin(object):
    @staticmethod
    def _needed_packages():
        """
        List of needed packages
        :return:
        """
        return []

    def _check_dependencies(self):
        """
        Raise error if dependencies are missing
        :return:
        """
        missing = []
        for package in self._needed_packages():
            if not is_package_available(package):
                missing.append(package)
        if len(missing) > 0:
            raise MissingDependencyError("Can't log " + str(self) + ". Missing dependencies: " + ", ".join(missing))


# noinspection PyBroadException
class LoggingFunction(DependencyMixin):
    __metaclass__ = ABCMeta
    """
    This class should be used to define new loggers
    """

    def __init__(self, **static_parameters):
        self._static_parameters = static_parameters

    def __pre__(self, ctx, *args, _pypads_env, **kwargs):
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
        raise NotImplementedError()

    # noinspection PyMethodMayBeStatic
    def _handle_failure(self, ctx, *args, _pypads_env: LoggingEnv, _pypads_error, **kwargs):
        try:
            mlflow.set_tag("pypads_failure", str(_pypads_error))
            exception(
                "Tracking failed for " + str(_pypads_env.call) + " with: " + str(
                    _pypads_error))
        except Exception:
            exception("Tracking failed for " + str(_pypads_env.call.call_id.instance) + " with: " + str(_pypads_error))

    def __call__(self, ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        """
        The call of the loggingFunction
        :param ctx:
        :param args:
        :param kwargs:
        :return:
        """
        from pypads.base import get_current_pads

        # Add the static parameters to our passed parameters
        _pypads_hook_params = {**self._static_parameters, **_pypads_env.parameter}

        # Call function to be executed before the tracked function
        _pypads_pre_return = None
        dependency_error = None

        if "no_intermediate" not in _pypads_hook_params or not _pypads_hook_params[
            "no_intermediate"] or not get_current_pads().api.is_intermediate_run():
            try:
                self._check_dependencies()
                _pypads_pre_return, time = timed(lambda: self.__pre__(ctx, *args, _pypads_env=_pypads_env,
                                                                      **{**_pypads_hook_params, **kwargs}))
                add_run_time(self,
                             str(_pypads_env.call) + "." + self.__class__.__name__ + ".__pre__",
                             time)
            except TimingDefined:
                # TODO multithreading fails
                pass
            except NotImplementedError:
                pass
            except MissingDependencyError as e:
                dependency_error = e
            except Exception as e:
                self._handle_failure(ctx, *args, _pypads_env=_pypads_env, _pypads_error=e, **kwargs)

        # Call the output producing code
        try:
            out, time = timed(
                lambda: self.call_wrapped(ctx, *args, _pypads_env=_pypads_env, _kwargs=kwargs, **_pypads_hook_params))
            try:
                add_run_time(None, str(_pypads_env.call), time)
            except TimingDefined as e:
                pass
        except Exception as e:
            error("Logging failed. " + str(e))
            original = _pypads_env.call.call_id.context.original(_pypads_env.callback)
            if callable(original):
                return original(ctx, *args, **kwargs)
            else:
                raise Exception("Couldn't fall back to original function for " + str(
                    _pypads_env.call.call_id.context.original_name(_pypads_env.callback)) + " on " + str(
                    _pypads_env.call.call_id.context) + ". Can't recover from " + str(e))

        if "no_intermediate" not in _pypads_hook_params or not _pypads_hook_params[
            "no_intermediate"] or not get_current_pads().api.is_intermediate_run():
            # Call function to be executed after the tracked function
            try:
                self._check_dependencies()
                _, time = timed(
                    lambda: self.__post__(ctx, *args, _pypads_env=_pypads_env,
                                          _pypads_result=out,
                                          _pypads_pre_return=_pypads_pre_return, **{**_pypads_hook_params, **kwargs}))
                add_run_time(self, str(_pypads_env.call) + "." + self.__class__.__name__ + ".__post__", time)
            except TimingDefined:
                pass
            except NotImplementedError:
                pass
            except MissingDependencyError as e:
                dependency_error = e
            except Exception as e:
                self._handle_failure(ctx, *args, _pypads_env=_pypads_env, _pypads_error=e, **kwargs)

        if dependency_error:
            warning(str(dependency_error))
        return out

    # noinspection PyMethodMayBeStatic
    def call_wrapped(self, ctx, *args, _pypads_env: LoggingEnv, _kwargs, **_pypads_hook_params):
        """
        The real call of the wrapped function. Be carefull when you change this.
        Exceptions here will not be catched automatically and might break your workflow.
        :param _pypads_env:
        :param _kwargs:
        :param ctx:
        :param args:
        :param _pypads_hook_params:
        :return:
        """
        return _pypads_env.callback(*args, **_kwargs)

    def __post__(self, ctx, *args, _pypads_env, _pypads_pre_return, _pypads_result, **kwargs):
        """
        The function to be called after executing the log anchor
        :param ctx:
        :param args:
        :param kwargs:
        :return:
        """
        raise NotImplementedError()
