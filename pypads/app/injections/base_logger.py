import os
import traceback
import uuid
from abc import abstractmethod, ABCMeta
from typing import Type

import mlflow
from pydantic import HttpUrl, BaseModel

from pypads import logger
from pypads.app.misc.mixins import DependencyMixin, DefensiveCallableMixin, TimedCallableMixin, \
    IntermediateCallableMixin, NoCallAllowedError, OrderMixin, ConfigurableCallableMixin, LibrarySpecificMixin, \
    FunctionHolderMixin, ProvenanceMixin
from pypads.importext.versioning import LibSelector
from pypads.injections.analysis.call_tracker import InjectionLoggingEnv, LoggingEnv
from pypads.injections.analysis.time_keeper import TimingDefined
from pypads.model.models import InjectionLoggerModel, InjectionLoggerCallModel, TrackedComponentModel, MetricMetaModel, \
    ParameterMetaModel, ArtifactMetaModel, LoggerOutputModel, TrackingObjectModel, RunLoggerModel, LoggerCallModel
from pypads.utils.logging_util import WriteFormats
from pypads.utils.util import inheritors


class PassThroughException(Exception):
    """
    Exception to be passed from _pre / _post and not be caught by the defensive logger.
    """

    def __init__(self, *args):
        super().__init__(*args)


class OriginalExecutor(FunctionHolderMixin, TimedCallableMixin):
    """
    Class adding a time tracking to the original execution given as fn.
    """

    def __init__(self, *args, fn, **kwargs):
        super().__init__(*args, fn=fn, **kwargs)


class LoggingExecutor(DefensiveCallableMixin, FunctionHolderMixin, TimedCallableMixin, ConfigurableCallableMixin):
    __metaclass__ = ABCMeta
    """
    Executor for the functionality a tracking function provides.
    """

    @abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        """
        Function to handle an error executing the logging functionality. In general this should add a failure tag and
        log to console.
        :param args: Arguments passed to the function
        :param ctx: Context of the function
        :param _pypads_env: Pypads environment
        :param error: Exception which was raised on the execution
        :param kwargs: Kwargs passed to the function
        :return:
        """
        try:
            raise error
        except TimingDefined:

            # Ignore if due to timing defined
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
                    "Tracking failed for " + str(_pypads_env.original_call) + " with: " + str(error))
            except Exception as e:
                logger.error(
                    "Tracking failed for " + str(_pypads_env.original_call.call_id.instance) + " with: " + str(error))
            return None, 0


class LoggerFunction(DefensiveCallableMixin, IntermediateCallableMixin, DependencyMixin,
                     LibrarySpecificMixin, ProvenanceMixin, ConfigurableCallableMixin, metaclass=ABCMeta):
    """
    Generic tracking function used for storing information to a backend.
    """

    is_a: HttpUrl = "https://www.padre-lab.eu/onto/tracking-function"

    # Default allow all libraries
    supported_libraries = {LibSelector(name=".*", constraint="*")}
    _stored_general_schema = False

    def __init__(self, *args, static_parameters=None, **kwargs):
        if static_parameters is None:
            static_parameters = {}
        super().__init__(*args, static_parameters=static_parameters, **kwargs)

    @classmethod
    def schema(cls):
        cls.schema()

    @classmethod
    def store_schema(cls):
        if not cls._stored_general_schema:
            from pypads.app.pypads import get_current_pads
            get_current_pads().api.log_mem_artifact(os.path.join(cls.__name__ + "_content_schema"),
                                                    cls.schema(), write_format=WriteFormats.json)
            cls._stored_general_schema = True


class LoggerCall(ProvenanceMixin):

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return LoggerCallModel

    def __init__(self, *args, logging_env: LoggingEnv, **kwargs):
        super().__init__(*args, **kwargs)
        self._logging_env = logging_env


class InjectionLoggerCall(LoggerCall):

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return InjectionLoggerCallModel

    def __init__(self, *args, logging_env: InjectionLoggingEnv, **kwargs):
        super().__init__(*args, call=logging_env.call, logging_env=logging_env, **kwargs)


class InjectionLoggerFunction(LoggerFunction, OrderMixin, metaclass=ABCMeta):
    is_a: HttpUrl = "https://www.padre-lab.eu/onto/injection-logger"

    def __init__(self, *args, static_parameters=None, **kwargs):
        super().__init__(*args, static_parameters=static_parameters, **kwargs)

        if not hasattr(self, "_pre"):
            self._pre = LoggingExecutor(fn=self.__pre__)
        if not hasattr(self, "_post"):
            self._post = LoggingExecutor(fn=self.__post__)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return InjectionLoggerModel

    def __pre__(self, ctx, *args, _logger_call, _args, _kwargs, **kwargs):
        """
        The function to be called before executing the log anchor. the value returned will be passed on to the __post__
        function as **_pypads_pre_return**.


        :return: _pypads_pre_return
        """
        pass

    def __post__(self, ctx, *args, _logger_call, _pypads_pre_return, _pypads_result, _args, _kwargs, **kwargs):
        """
        The function to be called after executing the log anchor.

        :param _pypads_pre_return: the value returned by __pre__.
        :param _pypads_result: the value returned by __call_wrapped__.

        :return: the wrapped function return value
        """
        pass

    def __real_call__(self, ctx, *args, _pypads_env: InjectionLoggingEnv, **kwargs):
        self.store_schema()

        _pypads_hook_params = {**self.static_parameters, **_pypads_env.parameter}

        logger_call = InjectionLoggerCall(logging_env=_pypads_env, logger_meta=self.model())

        # Trigger pre run functions
        _pre_result, pre_time = self._pre(ctx, _pypads_env=_pypads_env, _logger_call=logger_call, _args=args,
                                          _kwargs=kwargs,
                                          **_pypads_hook_params)
        logger_call.pre_time = pre_time

        # Trigger function itself
        _return, time = self.__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=args, _kwargs=kwargs,
                                              **_pypads_hook_params)
        logger_call.child_time = time

        # Trigger post run functions
        _post_result, post_time = self._post(ctx, _pypads_env=_pypads_env, _pypads_pre_return=_pre_result,
                                             _pypads_result=_return,
                                             _logger_call=logger_call,
                                             _args=args, _kwargs=kwargs, **_pypads_hook_params)
        logger_call.post_time = post_time
        logger_call.store()
        return _return

    def __call_wrapped__(self, ctx, *args, _pypads_env: InjectionLoggingEnv, _args, _kwargs, **_pypads_hook_params):
        """
        The real call of the wrapped function. Be carefull when you change this.
        Exceptions here will not be catched automatically and might break your workflow. The returned value will be passed on to __post__ function.

        :return: _pypads_result
        """
        _return, time = OriginalExecutor(fn=_pypads_env.callback)(*_args, **_kwargs)
        return _return, time

    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        """
        Handle error for DefensiveCallableMixin
        :param args:
        :param ctx:
        :param _pypads_env:
        :param error:
        :param kwargs:
        :return:
        """
        try:
            raise error
        except NoCallAllowedError as e:

            # Call next wrapped callback if no call was allowed due to the settings or environment
            _pypads_hook_params = {**self.static_parameters, **_pypads_env.parameter}
            return self.__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=args, _kwargs=kwargs,
                                         **_pypads_hook_params)
        except Exception as e:
            logger.error("Logging failed for " + str(self) + ": " + str(error) + "\nTrace:\n" + traceback.format_exc())

            # Try to call the original unwrapped function if something broke
            original = _pypads_env.original_call.call_id.context.original(_pypads_env.callback)
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
                    _pypads_env.original_call.call_id.context.original_name(_pypads_env.callback)) + " on " + str(
                    _pypads_env.original_call.call_id.context) + ". Can't recover from " + str(error))


class LoggerTrackingObject(ProvenanceMixin):
    is_a = "https://www.padre-lab.eu/onto/tracking_object"

    def __init__(self, *args, call: LoggerCall, model_cls: Type[TrackingObjectModel], **kwargs):
        super().__init__(*args, model_cls=model_cls, original_call=call, **kwargs)
        self._component_model = TrackedComponentModel(tracking_component=self._base_path())
        self._known_metrics = set()
        self._known_params = set()
        self._known_artifacts = set()
        self._produced_output = False

    def _add_logger_output(self):
        self._produced_output = True
        if self.call.output is None:
            uid = uuid.uuid4()
            self.call.output = LoggerOutputModel(uid=uid, uri="{}-output#{}".format(self.uri, uid),
                                                 defined_in=self.defined_in)
        self.call.output.objects.append(self._component_model)

    def _store_metric(self, val, meta: MetricMetaModel, step=0):
        from pypads.app.pypads import get_current_pads
        get_current_pads().api.log_metric(meta.name, val, step=step)
        if meta.name not in self._known_metrics:
            self._known_metrics.add(meta.name)
            self._component_model.metrics.append(meta.name)
            if not self._produced_output:
                self._add_logger_output()

    def _store_param(self, val, meta: ParameterMetaModel):
        from pypads.app.pypads import get_current_pads
        get_current_pads().api.log_param(meta.name, val)
        if meta.name not in self._known_params:
            self._known_params.add(meta.name)
            self._component_model.parameters.append(meta.name)
            if not self._produced_output:
                self._add_logger_output()

    def _store_artifact(self, val, meta: ArtifactMetaModel):
        from pypads.app.pypads import get_current_pads
        get_current_pads().api.log_mem_artifact(meta.path, val, write_format=meta.format)
        if meta.path not in self._known_artifacts:
            self._known_artifacts.add(meta.path)
            self._component_model.artifacts.append(meta.path)
            if not self._produced_output:
                self._add_logger_output()

    def _base_path(self):
        return os.path.join(self.call.created_by.name, self.__class__.__name__)

    def meta_json(self):
        """
        Returns a json referencing stored tracking objects, parameters, artifacts and metrics
        :return:
        """
        return self._component_model.json()

    def meta_schema(self):
        """
        Returns a json schema for referencing stored tracking objects, parameters, artifacts and metrics
        :return:
        """
        return self._component_model.schema()


def logging_functions():
    """
    Find all post run functions defined in our imported context.
    :return:
    """
    return inheritors(InjectionLoggerFunction)
