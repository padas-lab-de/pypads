import traceback
from _py_abc import ABCMeta
from abc import abstractmethod

import mlflow
from loguru import logger

from pypads.functions.analysis.call_tracker import LoggingEnv
from pypads.functions.analysis.time_keeper import TimingDefined, add_run_time
from pypads.functions.loggers.mixins import DependencyMixin, DefensiveCallableMixin, TimedCallableMixin, \
    IntermediateCallableMixin, NoCallAllowedError, OrderMixin, ConfigurableCallableMixin


class PassThroughException(Exception):
    """
    Exception to be passed from _pre / _post and not be caught by the defensive logger.
    """

    def __init__(self, *args):
        super().__init__(*args)


class FunctionWrapper(TimedCallableMixin):
    """
    Holds the given function in a timed callable.
    """

    def __init__(self, *args, fn, **kwargs):
        super().__init__(*args, **kwargs)
        self._fn = fn

    @property
    def fn(self):
        return self._fn

    def __real_call__(self, *args, **kwargs):
        return self._fn(*args, **kwargs)


class LoggingExecutor(DefensiveCallableMixin, FunctionWrapper, ConfigurableCallableMixin):
    __metaclass__ = ABCMeta
    """
    Pre or Post executor for the logging function.
    """

    @abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        try:
            raise error
        except TimingDefined:
            # TODO multithreading fails
            pass
        except NotImplementedError:

            # Ignore if only pre or post where defined
            return None, 0
        except (NoCallAllowedError, PassThroughException) as e:

            # Pass No Call Allowed Error through
            raise e
        except Exception as e:

            # Catch other exceptions for this single logger
            try:
                mlflow.set_tag("pypads_failure", str(error))
                logger.error(
                    "Tracking failed for " + str(_pypads_env.call) + " with: " + str(error))
            except Exception as e:
                logger.error("Tracking failed for " + str(_pypads_env.call.call_id.instance) + " with: " + str(error))
            return None, 0


# noinspection PyBroadException
class LoggingFunction(DefensiveCallableMixin, IntermediateCallableMixin, DependencyMixin, OrderMixin):
    __metaclass__ = ABCMeta
    """
    This class should be used to define new loggers.
    """

    def __init__(self, *args, static_parameters=None, **kwargs):
        super().__init__(*args, **kwargs)
        if static_parameters is None:
            static_parameters = {}
        self._static_parameters = static_parameters

        if not hasattr(self, "_pre"):
            self._pre = LoggingExecutor(fn=self.__pre__)
        if not hasattr(self, "_post"):
            self._post = LoggingExecutor(fn=self.__post__)

    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        try:
            raise error
        except NoCallAllowedError as e:

            # Call next wrapped callback if no call was allowed due to the settings or environment
            _pypads_hook_params = {**self._static_parameters, **_pypads_env.parameter}
            return self.__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=args, _kwargs=kwargs,
                                         **_pypads_hook_params)
        except Exception as e:
            logger.error("Logging failed for " + str(self) + ": " + str(error) + "\nTrace:\n" + traceback.format_exc())

            # Try to call the original unwrapped function if something broke
            original = _pypads_env.call.call_id.context.original(_pypads_env.callback)
            if callable(original):
                try:
                    logger.error("Trying to recover from: " + str(e))
                    out = original(ctx, *args, **kwargs)
                    logger.success("Succeeded recovering on error : " + str(e))
                    return out
                except TypeError as e:
                    logger.error("Recovering failed due to: " + str(
                        e) + ". Trying to call without passed ctx. This might be due to an error in the wrapping.")
                    out = original(*args, **kwargs)
                    logger.success("Succeeded recovering on error : " + str(e))
                    return out
            else:

                # Original function was not accessiblete
                raise Exception("Couldn't fall back to original function for " + str(
                    _pypads_env.call.call_id.context.original_name(_pypads_env.callback)) + " on " + str(
                    _pypads_env.call.call_id.context) + ". Can't recover from " + str(error))

    def __pre__(self, ctx, *args, _pypads_env, _args, _kwargs, **kwargs):
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

    def __post__(self, ctx, *args, _pypads_env, _pypads_pre_return, _pypads_result, _args, _kwargs, **kwargs):
        """
        The function to be called after executing the log anchor
        :param ctx:
        :param args:
        :param kwargs:
        :return:
        """
        raise NotImplementedError()

    def _extract_runtime(self, out, _pypads_env, label):
        if type(out) is tuple and len(out) is 2:
            _return = out[0]
            time = out[1]
            if time != 0:
                add_run_time(self, str(_pypads_env.call) + "." + self.__class__.__name__ + "." + label, time)

    def __real_call__(self, ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        # Add the static parameters to our passed parameters
        _pypads_hook_params = {**self._static_parameters, **_pypads_env.parameter}

        _pre_result = None
        try:

            out = self._pre(ctx, _pypads_env=_pypads_env, _args=args, _kwargs=kwargs,
                            **_pypads_hook_params)
            self._extract_runtime(out, _pypads_env, "__pre__")
        except TimingDefined:
            pass
        _return = self.__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=args, _kwargs=kwargs, **_pypads_hook_params)

        try:
            out = self._post(ctx, _pypads_pre_return=_pre_result, _pypads_result=_return, _pypads_env=_pypads_env,
                             _args=args, _kwargs=kwargs, **_pypads_hook_params)
            self._extract_runtime(out, _pypads_env, "__post__")
        except TimingDefined:
            pass
        return _return

    def __call_wrapped__(self, ctx, *args, _pypads_env: LoggingEnv, _args, _kwargs, **_pypads_hook_params):
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
        _return, time = FunctionWrapper(fn=_pypads_env.callback)(*_args, **_kwargs)
        try:
            add_run_time(None, str(_pypads_env.call), time)
        except TimingDefined as e:
            pass
        return _return
