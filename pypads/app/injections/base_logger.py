import traceback
from abc import abstractmethod, ABCMeta
from collections import OrderedDict
from typing import Set

import mlflow

from pypads import logger
from pypads.app.misc.mixins import DependencyMixin, DefensiveCallableMixin, TimedCallableMixin, \
    IntermediateCallableMixin, NoCallAllowedError, OrderMixin, ConfigurableCallableMixin, CallableMixin, SuperStop
from pypads.importext.mappings import LibSelector
from pypads.injections.analysis.call_tracker import LoggingEnv
from pypads.injections.analysis.time_keeper import TimingDefined, add_run_time
from pypads.utils.util import inheritors

ANY_SELECTOR = LibSelector(".*", "*")


class LibrarySpecificMixin(SuperStop):
    __metaclass__ = ABCMeta

    @staticmethod
    def supported_libraries() -> Set[LibSelector]:
        s = set()
        s.add(ANY_SELECTOR)
        return s

    def allows_any(self, lib_selector: LibSelector):
        if ANY_SELECTOR in self.supported_libraries():
            return True
        return any([s.allows_any(lib_selector) for s in self.supported_libraries()])

    def allows(self, name, version):
        if ANY_SELECTOR in self.supported_libraries():
            return True
        return any([s.allows(version) for s in self.supported_libraries() if s == name])

    def is_applicable(self, lib_selector: LibSelector, only_name=True):
        if self.allows_any(lib_selector):
            return True
        if only_name:
            for s in self.supported_libraries():
                if s.name == lib_selector.name:
                    return True
        return False


class PassThroughException(Exception):
    """
    Exception to be passed from _pre / _post and not be caught by the defensive logger.
    """

    def __init__(self, *args):
        super().__init__(*args)


class FunctionHolder(CallableMixin):
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


class OriginalExecutor(FunctionHolder, TimedCallableMixin):
    """
    Class adding a time tracking to the original execution given as fn.
    """

    def __init__(self, *args, fn, **kwargs):
        super().__init__(*args, fn=fn, **kwargs)


class LoggingExecutor(DefensiveCallableMixin, FunctionHolder, TimedCallableMixin, ConfigurableCallableMixin):
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
class LoggingFunction(DefensiveCallableMixin, IntermediateCallableMixin, DependencyMixin, OrderMixin,
                      LibrarySpecificMixin, metaclass=ABCMeta):
    """
    This class should be used to define new custom loggers. The user has to define __pre__ and/or __post__ methods
    depending on the specific use case.

    :param static_parameters: dict, optional, static parameters (if needed) to be used when logging.

    .. note:: It is not recommended to change the __call_wrapped__ method, only if really needed.

    """

    def __init__(self, *args, static_parameters=None, identity=None, **kwargs):
        super().__init__(*args, **kwargs)
        if static_parameters is None:
            static_parameters = {}
        self._static_parameters = static_parameters
        self._identify = identity

        if not hasattr(self, "_pre"):
            self._pre = LoggingExecutor(fn=self.__pre__)
        if not hasattr(self, "_post"):
            self._post = LoggingExecutor(fn=self.__post__)

    @property
    def identity(self):
        """
        Return the identity of the logger. This should be unique for the same functionality across multiple versions.
        :return:
        """
        return self._identify

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
        The function to be called before executing the log anchor. the value returned will be passed on to the __post__
        function as **_pypads_pre_return**.


        :return: _pypads_pre_return
        """
        pass

    def __post__(self, ctx, *args, _pypads_env, _pypads_pre_return, _pypads_result, _args, _kwargs, **kwargs):
        """
        The function to be called after executing the log anchor.

        :param _pypads_pre_return: the value returned by __pre__.
        :param _pypads_result: the value returned by __call_wrapped__.

        :return: the wrapped function return value
        """
        pass

    def _extract_runtime(self, out, _pypads_env, label):
        if type(out) is tuple and len(out) is 2:
            _return = out[0]
            time = out[1]
            if time != 0:
                add_run_time(self, str(_pypads_env.call) + "." + self.__class__.__name__ + "." + label, time)
                return time
        return None

    def _check_object_store(self, pre_time=None, call_time=None, post_time=None):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        if pads.cache.run_exists(id(self)):
            objects_store: OrderedDict = pads.cache.run_get(id(self))
            for k, o in objects_store.items():
                obj = o[0]
                if o[1]:
                    obj.add_timings(pre=pre_time, call=call_time, post=post_time)
                    obj.store()
                    objects_store.pop(k)

            pads.cache.run_add(id(self), objects_store)

    def __real_call__(self, ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        _pypads_hook_params = {**self._static_parameters, **_pypads_env.parameter}

        _pre_result = None
        _pre_time = None
        try:

            _pre_result = self._pre(ctx, _pypads_env=_pypads_env, _args=args, _kwargs=kwargs,
                                    **_pypads_hook_params)
            _pre_time = self._extract_runtime(_pre_result, _pypads_env, "__pre__")
        except TimingDefined:
            pass
        _return, time = self.__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=args, _kwargs=kwargs,
                                              **_pypads_hook_params)

        _post_time = None
        try:
            out = self._post(ctx, _pypads_pre_return=_pre_result, _pypads_result=_return, _pypads_env=_pypads_env,
                             _args=args, _kwargs=kwargs, **_pypads_hook_params)
            _post_time = self._extract_runtime(out, _pypads_env, "__post__")
        except TimingDefined:
            pass

        self._check_object_store(pre_time=_pre_time, post_time=_post_time, call_time=time)

        return _return

    def __call_wrapped__(self, ctx, *args, _pypads_env: LoggingEnv, _args, _kwargs, **_pypads_hook_params):
        """
        The real call of the wrapped function. Be carefull when you change this.
        Exceptions here will not be catched automatically and might break your workflow. The returned value will be passed on to __post__ function.

        :return: _pypads_result
        """
        _return, time = OriginalExecutor(fn=_pypads_env.callback)(*_args, **_kwargs)
        return _return, time


def logging_functions():
    """
    Find all post run functions defined in our imported context.
    :return:
    """
    return inheritors(LoggingFunction)
