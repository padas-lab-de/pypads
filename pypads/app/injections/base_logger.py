import os
import traceback
from abc import abstractmethod, ABCMeta
from typing import Type, Set, List, Callable

import mlflow
from pydantic import HttpUrl, BaseModel

from pypads.app.env import LoggerEnv
from pypads import logger
from pypads.app.misc.mixins import DependencyMixin, DefensiveCallableMixin, TimedCallableMixin, \
    IntermediateCallableMixin, NoCallAllowedError, ConfigurableCallableMixin, LibrarySpecificMixin, \
    FunctionHolderMixin, ProvenanceMixin, BaseDefensiveCallableMixin
from pypads.importext.versioning import LibSelector
from pypads.injections.analysis.time_keeper import TimingDefined
from pypads.model.models import MetricMetaModel, \
    ParameterMetaModel, ArtifactMetaModel, TrackedObjectModel, LoggerCallModel, OutputModel, EmptyOutput, TagMetaModel
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
                                                path=self.created_by + "Calls")


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
        pads = get_current_pads()
        consolidated_json = pads.cache.get('consolidated_dict', None)
        if consolidated_json is not None:
            metrics_dict = consolidated_json.get('metrics', {})
            metrics_list = metrics_dict.get(meta.name, [])
            metrics_list.append(val)
            metrics_dict[meta.name] = metrics_list
            consolidated_json['metrics'] = metrics_dict
            pads.cache.add('consolidated_dict', consolidated_json)
        pads.api.log_metric(meta.name, val, meta=meta)

    @staticmethod
    def _store_param(val, meta: ParameterMetaModel):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        consolidated_json = pads.cache.get('consolidated_dict', None)
        if consolidated_json is not None:
            # Set the parameter
            estimator_name = meta.name[:meta.name.rfind('.')]
            parameters = consolidated_json.get('parameters', {})
            estimator_dict = parameters.get(estimator_name, {})
            estimator_dict[meta.name.split(sep='.')[-1]] = val

            # Store the dictionaries back into the cache
            parameters[estimator_name] = estimator_dict
            consolidated_json['parameters'] = parameters
            pads.cache.add('consolidated_dict', consolidated_json)

        get_current_pads().api.log_param(meta.name, val, meta=meta)

    @staticmethod
    def _store_artifact(val, meta: ArtifactMetaModel):
        from pypads.app.pypads import get_current_pads
        get_current_pads().api.log_mem_artifact(meta.path, val, meta=meta, write_format=meta.format)

    @staticmethod
    def _store_tag(val, meta: TagMetaModel):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        consolidated_json = pads.cache.get('consolidated_dict', None)
        if consolidated_json is not None:
            tags = consolidated_json.get('tags', dict())
            tags[meta.name] = val
            consolidated_json['tags'] = tags
            pads.cache.add('consolidated_json', consolidated_json)
        pads.api.set_tag(meta.name, val)

    def _base_path(self):
        return os.path.join(self.tracked_by.created_by, "TrackedObjects", self.__class__.__name__)

    def _get_artifact_path(self, name):
        return os.path.join(str(id(self)),name)

    def store(self, output, key="tracked_object", *json_path):
        """
        :param output:
        :param key: Name of the tracking object in the schema
        :param json_path: path in the output schema
        :return:
        """
        output.add_tracked_object(self, key, *json_path)


class LoggerOutput(ProvenanceMixin):

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return OutputModel

    def add_tracked_object(self, to: TrackedObject, key, *json_path):
        curr = self
        for p in json_path:
            curr = getattr(curr, p)
        if hasattr(curr, key):
            attr = getattr(curr, key)
            if isinstance(attr, List):
                attr.append(to)
                to = attr
            elif isinstance(attr, Set):
                attr.add(to)
                to = attr
        setattr(curr, key, to)

    def store(self, path=""):
        from pypads.app.pypads import get_current_pads
        return get_current_pads().api.store_logger_output(self, path)

    def set_failure_state(self, e: Exception):
        self.failed = "Logger Output might be inaccurate/corrupt due to exception in execution: '{}'".format(str(e))


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
        self._cleanup_fns = {}

    @classmethod
    def build_output(cls, **kwargs):
        schema_class = cls.output_schema_class()

        class OutputModelHolder(LoggerOutput):

            @classmethod
            def get_model_cls(cls) -> Type[BaseModel]:
                return schema_class

        return OutputModelHolder(**kwargs)

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return EmptyOutput

    @classmethod
    def output_schema(cls):
        return cls.output_schema_class().schema()

    @classmethod
    def _default_output_class(cls, clazz: Type[TrackedObject]) -> Type[OutputModel]:
        class DefaultOutput(OutputModel):
            tracked_object: clazz.get_model_cls() = ...  # Path to tracking objects

            class Config:
                orm_mode = True

        return DefaultOutput

    @classmethod
    def store_schema(cls, path=None):
        if not cls._schema_path:
            path = path or ""
            from pypads.app.pypads import get_current_pads
            schema_path = os.path.join(path, cls.__name__ + "_schema")
            get_current_pads().api.log_mem_artifact(schema_path,
                                                    cls.schema(), write_format=WriteFormats.json)
            get_current_pads().api.log_mem_artifact(os.path.join(path, cls.__name__ + "_output_schema"),
                                                    cls.output_schema(), write_format=WriteFormats.json)
            cls._schema_path = path
        return cls._schema_path

    @abstractmethod
    def _base_path(self):
        return "Loggers/"

    def cleanup_fns(self, call: LoggerCall) -> List[Callable]:
        return self._cleanup_fns[call] if call in self._cleanup_fns.keys() else []

    def register_cleanup_fn(self, call: LoggerCall, fn):
        if call not in self._cleanup_fns:
            self._cleanup_fns[call] = []
        self._cleanup_fns[call].append(fn)


class SimpleLogger(Logger):

    def __init__(self, *args, fn=None, **kwargs):
        super().__init__(*args, **kwargs)
        if fn is None:
            fn = self._call
        if not hasattr(self, "_fn"):
            self._fn = LoggerExecutor(fn=fn)

    @property
    def __name__(self):
        if self._fn.fn != self._call:
            return self._fn.fn.__name__
        else:
            return self.__class__.__name__

    def _call(self, _pypads_env: LoggerEnv, _logger_call: LoggerCall, _logger_output,*args, **kwargs):
        """
        Function where to add you custom code to execute before starting or ending the run.

        :param pads: the current instance of PyPads.
        """
        pass

    def __real_call__(self, *args, _pypads_env: LoggerEnv, **kwargs):
        self.store_schema(self._base_path())

        _pypads_params = _pypads_env.parameter

        logger_call = self.build_call_object(_pypads_env, created_by=self.store_schema(self._base_path()))
        output = self.build_output()

        try:
            _return, time = self._fn(*args, _pypads_env=_pypads_env, _logger_call=logger_call, _logger_output=output,
                                     _pypads_params=_pypads_params,
                                     **{**self.static_parameters, **kwargs})

            logger_call.execution_time = time
        except Exception as e:
            logger_call.failed = str(e)
            output.set_failure_state(e)
            raise e
        finally:
            for fn in self.cleanup_fns(logger_call):
                fn(self, logger_call)
            logger_call.output = output.store(self._base_path())
            logger_call.store()
        return _return

    @abstractmethod
    def build_call_object(self, _pypads_env, **kwargs):
        raise NotImplementedError()
