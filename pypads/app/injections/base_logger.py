import os
import uuid
from abc import abstractmethod, ABCMeta
from typing import Type

import mlflow
from pydantic import HttpUrl, BaseModel

from pypads import logger
from pypads.app.misc.mixins import DependencyMixin, DefensiveCallableMixin, TimedCallableMixin, \
    IntermediateCallableMixin, NoCallAllowedError, ConfigurableCallableMixin, LibrarySpecificMixin, \
    FunctionHolderMixin, ProvenanceMixin
from pypads.importext.versioning import LibSelector
from pypads.injections.analysis.call_tracker import LoggingEnv
from pypads.injections.analysis.time_keeper import TimingDefined
from pypads.model.models import TrackedComponentModel, MetricMetaModel, \
    ParameterMetaModel, ArtifactMetaModel, LoggerOutputModel, TrackingObjectModel, LoggerCallModel
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

    # @classmethod
    # def schema(cls):
    #     cls.schema()

    @classmethod
    def store_schema(cls):
        if not cls._stored_general_schema:
            from pypads.app.pypads import get_current_pads
            get_current_pads().api.log_mem_artifact(os.path.join(cls.__name__ + "_content_schema"),
                                                    cls.schema(cls), write_format=WriteFormats.json)
            cls._stored_general_schema = True


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


class LoggerTrackingObject(ProvenanceMixin):
    is_a = "https://www.padre-lab.eu/onto/tracking_object"

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return TrackingObjectModel

    def __init__(self, *args, call: LoggerCall, **kwargs):
        super().__init__(*args,  original_call=call, **kwargs)
        self._component_model = TrackedComponentModel(tracking_component=self._base_path())
        self._known_metrics = set()
        self._known_params = set()
        self._known_artifacts = set()
        self._produced_output = False

    def _add_logger_output(self):
        self._produced_output = True
        if self.tracked_by.output is None:
            uid = uuid.uuid4()
            self.tracked_by.output = LoggerOutputModel(uid=uid, uri="{}-output#{}".format(self.uri, uid))
        self.tracked_by.output.objects.append(self._component_model)

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

