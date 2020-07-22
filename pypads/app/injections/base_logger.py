import os
from abc import abstractmethod, ABCMeta
from typing import Type, Set

import mlflow
from pydantic import HttpUrl, BaseModel

from app.env import LoggingEnv
from pypads import logger
from pypads.app.misc.mixins import DependencyMixin, DefensiveCallableMixin, TimedCallableMixin, \
    IntermediateCallableMixin, NoCallAllowedError, ConfigurableCallableMixin, LibrarySpecificMixin, \
    FunctionHolderMixin, ProvenanceMixin, BaseDefensiveCallableMixin
from pypads.importext.versioning import LibSelector
from pypads.injections.analysis.time_keeper import TimingDefined
from pypads.model.models import MetricMetaModel, \
    ParameterMetaModel, ArtifactMetaModel, TrackedObjectModel, LoggerCallModel
from pypads.utils.logging_util import WriteFormats


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
                    "Tracking failed for " + str(_pypads_env.call) + " with: " + str(error))
            except Exception as e:
                logger.error(
                    "Tracking failed for " + str(_pypads_env.call.call_id.instance) + " with: " + str(error))
            return None, 0


class LoggerCall(ProvenanceMixin):

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return LoggerCallModel

    def __init__(self, *args, logging_env: LoggingEnv, **kwargs):
        super().__init__(*args, **kwargs)
        self._logging_env = logging_env

    def store(self):
        from pypads.app.pypads import get_current_pads
        from pypads.utils.logging_util import WriteFormats
        get_current_pads().api.log_mem_artifact(str(self.uid), self.json(), WriteFormats.json.value,
                                                path=self.created_by.name)


class TrackedObject(ProvenanceMixin):
    is_a = "https://www.padre-lab.eu/onto/tracking_object"

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return TrackedObjectModel

    def __init__(self, *args, call: LoggerCall, **kwargs):
        super().__init__(*args, original_call=call, **kwargs)

    @staticmethod
    def _store_metric(val, meta: MetricMetaModel):
        from pypads.app.pypads import get_current_pads
        get_current_pads().api.log_metric(meta.name, val, step=meta.step)

    @staticmethod
    def _store_param(val, meta: ParameterMetaModel):
        from pypads.app.pypads import get_current_pads
        get_current_pads().api.log_param(meta.name, val)

    @staticmethod
    def _store_artifact(val, meta: ArtifactMetaModel):
        from pypads.app.pypads import get_current_pads
        get_current_pads().api.log_mem_artifact(meta.path, val, write_format=meta.format)

    def _base_path(self):
        return os.path.join(self.call.created_by.name, self.__class__.__name__)

    def store(self):
        from pypads.app.pypads import get_current_pads
        get_current_pads().api.store_tracked_object(self)


class LoggerFunction(BaseDefensiveCallableMixin, IntermediateCallableMixin, DependencyMixin,
                     LibrarySpecificMixin, ProvenanceMixin, ConfigurableCallableMixin, metaclass=ABCMeta):
    """
    Generic tracking function used for storing information to a backend.
    """

    is_a: HttpUrl = "https://www.padre-lab.eu/onto/tracking-function"

    # Default allow all libraries
    supported_libraries = {LibSelector(name=".*", constraint="*")}
    _stored_general_schema = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tracked_objects: Set[TrackedObject] = set()

    @classmethod
    def output_schema_class(cls):
        class EmptyOutput(BaseModel):
            pass

        return EmptyOutput

    @classmethod
    def output_schema(cls):
        return cls.output_schema_class().schema()

    @classmethod
    def _default_output_class(cls, clazz):
        class OutputClass(BaseModel):
            output: clazz = ...

        return OutputClass

    def add_tracking_object(self, to: TrackedObject):
        self._tracked_objects.add(to)

    def store_output(self):
        for t in self._tracked_objects:
            t.store()

    @classmethod
    def store_schema(cls):
        if not cls._stored_general_schema:
            from pypads.app.pypads import get_current_pads
            get_current_pads().api.log_mem_artifact(os.path.join(cls.__name__ + "_schema"),
                                                    cls.schema(), write_format=WriteFormats.json)
            get_current_pads().api.log_mem_artifact(os.path.join(cls.__name__ + "_output_schema"),
                                                    cls.output_schema(), write_format=WriteFormats.json)
            cls._stored_general_schema = True
