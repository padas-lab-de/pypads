import os
import traceback
from abc import abstractmethod, ABCMeta
from typing import Type, Set

import mlflow
from pydantic import HttpUrl, BaseModel

from app.env import LoggerEnv
from pypads import logger
from pypads.app.misc.mixins import DependencyMixin, DefensiveCallableMixin, TimedCallableMixin, \
    IntermediateCallableMixin, NoCallAllowedError, ConfigurableCallableMixin, LibrarySpecificMixin, \
    FunctionHolderMixin, ProvenanceMixin, BaseDefensiveCallableMixin
from pypads.importext.versioning import LibSelector
from pypads.injections.analysis.time_keeper import TimingDefined
from pypads.model.metadata import ModelObject
from pypads.model.models import MetricMetaModel, \
    ParameterMetaModel, ArtifactMetaModel, TrackedObjectModel, LoggerCallModel, OutputModel
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


class LoggerExecutor(DefensiveCallableMixin, FunctionHolderMixin, TimedCallableMixin, ConfigurableCallableMixin):
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
            except Exception as e:
                pass
            logger.error(
                f"Tracking failed for {str(_pypads_env)} with: {str(error)} \nTrace:\n{traceback.format_exc()}")
            return None, 0


class TrackedObject(ProvenanceMixin):
    is_a = "https://www.padre-lab.eu/onto/tracked_object"

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return TrackedObjectModel

    def __init__(self, *args, tracked_by, **kwargs):
        super().__init__(*args, tracked_by=tracked_by, **kwargs)

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
        return os.path.join(self.tracked_by.created_by, self.__class__.__name__)

    def store(self, key="value", *json_path):
        """
        :param key: Name of the tracking object in the schema
        :param json_path: path in the output schema
        :return:
        """
        self.tracked_by.output.add_tracked_object(self, key, *json_path)


class OutputModelHolder(ModelObject, metaclass=ABCMeta):

    def add_tracked_object(self, to: TrackedObject, key, *json_path):
        curr = self
        for p in json_path:
            curr = getattr(curr, p)
        setattr(curr, key, to.store())


class LoggerCall(ProvenanceMixin):

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return LoggerCallModel

    def __init__(self, *args, logging_env: LoggerEnv, **kwargs):
        super().__init__(*args, **kwargs)
        self._logging_env = logging_env

    def store(self):
        from pypads.app.pypads import get_current_pads
        from pypads.utils.logging_util import WriteFormats
        get_current_pads().api.log_mem_artifact("{}".format(str(self.uid)), self.json(), WriteFormats.json.value,
                                                path=self.created_by)


class EmptyOutput(OutputModel):
    is_a: HttpUrl = "https://www.padre-lab.eu/onto/EmptyLoggerOutput"

    class Config:
        orm_mode = True


class Logger(BaseDefensiveCallableMixin, IntermediateCallableMixin, DependencyMixin,
             LibrarySpecificMixin, ProvenanceMixin, ConfigurableCallableMixin, metaclass=ABCMeta):
    """
    Generic tracking function used for storing information to a backend.
    """

    is_a: HttpUrl = "https://www.padre-lab.eu/onto/tracking-function"

    # Default allow all libraries
    supported_libraries = {LibSelector(name=".*", constraint="*")}
    _schema_path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tracked_objects: Set[TrackedObject] = set()

    @classmethod
    def build_output(cls, **kwargs):
        schema_class = cls.output_schema_class()

        class DynamicOutputModelHolder(OutputModelHolder):
            is_a = "https://www.padre-lab.eu/onto/output_model"

            @classmethod
            def get_model_cls(cls) -> Type[BaseModel]:
                return schema_class

        return DynamicOutputModelHolder(**kwargs)

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return EmptyOutput

    @classmethod
    def output_schema(cls):
        return cls.output_schema_class().schema()

    @classmethod
    def _default_output_class(cls, clazz: Type[TrackedObject]) -> Type[OutputModel]:
        class OutputClass(OutputModel):
            value: clazz.get_model_cls() = ...

            class Config:
                orm_mode = True
                arbitrary_types_allowed = True
        return OutputClass

    @classmethod
    def store_schema(cls):
        if not cls._schema_path:
            from pypads.app.pypads import get_current_pads
            schema_path = os.path.join(cls.__name__ + "_schema")
            get_current_pads().api.log_mem_artifact(schema_path,
                                                    cls.schema(), write_format=WriteFormats.json)
            get_current_pads().api.log_mem_artifact(os.path.join(cls.__name__ + "_output_schema"),
                                                    cls.output_schema(), write_format=WriteFormats.json)
            cls._schema_path = schema_path
        return cls._schema_path


class SimpleLogger(Logger):

    def __init__(self, *args, fn=None, **kwargs):
        super().__init__(*args, **kwargs)
        if fn is None:
            fn = self._call
        if not hasattr(self, "_fn"):
            self._fn = LoggerExecutor(fn=fn)

    @property
    def __name__(self):
        if self._fn.fn is not self._call:
            return self._fn.fn.__name__
        else:
            return self.__class__.__name__

    def _call(self, _pypads_env: LoggerEnv, *args, **kwargs):
        """
        Function where to add you custom code to execute before starting or ending the run.

        :param pads: the current instance of PyPads.
        """
        pass

    def __real_call__(self, *args, _pypads_env: LoggerEnv, **kwargs):
        self.store_schema()

        _pypads_params = _pypads_env.parameter

        logger_call = self.build_call_object(_pypads_env, created_by=self.store_schema())
        output = self.build_output(tracked_by=logger_call)
        logger_call.output = output

        try:
            _return, time = self._fn(*args, _pypads_env=_pypads_env, _logger_call=logger_call,
                                     _pypads_params=_pypads_params,
                                     **kwargs)

            logger_call.execution_time = time
        except Exception as e:
            logger_call.failed = str(e)
            raise e
        finally:
            logger_call.store()
        return _return

    @abstractmethod
    def build_call_object(self, _pypads_env, **kwargs):
        raise NotImplementedError()
