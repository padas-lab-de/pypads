import os
import traceback
from abc import abstractmethod, ABCMeta
from typing import Type, Set, List, Callable, Optional

import mlflow
from pydantic import HttpUrl, BaseModel

from pypads import logger
from pypads.app.env import LoggerEnv
from pypads.app.misc.mixins import DependencyMixin, DefensiveCallableMixin, TimedCallableMixin, \
    IntermediateCallableMixin, NoCallAllowedError, ConfigurableCallableMixin, LibrarySpecificMixin, \
    FunctionHolderMixin, ProvenanceMixin, BaseDefensiveCallableMixin
from pypads.arguments import ontology_uri
from pypads.importext.versioning import LibSelector
from pypads.injections.analysis.time_keeper import TimingDefined
from pypads.model.logger_call import LoggerCallModel
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.logging_util import FileFormats
from pypads.utils.util import dict_merge, persistent_hash


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
        from pypads.utils.logging_util import FileFormats
        get_current_pads().api.log_mem_artifact("{}".format(str(self.uid)), self.json(by_alias=True),
                                                FileFormats.json.value, path=self.created_by + "Calls")


class TrackedObject(ProvenanceMixin):
    """
    A collection of tracked information
    """
    is_a = f"{ontology_uri}tracked_object"

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return TrackedObjectModel

    def __init__(self, *args, tracked_by, **kwargs):
        super().__init__(*args, tracked_by=tracked_by, **kwargs)

    @staticmethod
    def store_metric(key, value, description="", step=None, meta: dict = None):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        # consolidated_json = pads.cache.get('consolidated_dict', None)
        # if consolidated_json is not None:
        #     metrics_dict = consolidated_json.get('metrics', {})
        #     metrics_list = metrics_dict.get(meta.name, [])
        #     metrics_list.append(val)
        #     metrics_dict[meta.name] = metrics_list
        #     consolidated_json['metrics'] = metrics_dict
        #     pads.cache.add('consolidated_dict', consolidated_json)
        pads.api.log_metric(key, value, description=description, step=step, meta=meta)

    @staticmethod
    def store_param(key, value, description="", meta: dict = None):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        # consolidated_json = pads.cache.get('consolidated_dict', None)
        # if consolidated_json is not None:
        #     # Set the parameter
        #     estimator_name = meta.name[:meta.name.rfind('.')]
        #     parameters = consolidated_json.get('parameters', {})
        #     estimator_dict = parameters.get(estimator_name, {})
        #     estimator_dict[meta.name.split(sep='.')[-1]] = val
        #
        #     # Store the dictionaries back into the cache
        #     parameters[estimator_name] = estimator_dict
        #     consolidated_json['parameters'] = parameters
        #     pads.cache.add('consolidated_dict', consolidated_json)

        pads.api.log_param(key, value, description=description, meta=meta)

    @staticmethod
    def store_artifact(self, name, obj, write_format=FileFormats.text, description="", path=None, meta=None):
        from pypads.app.pypads import get_current_pads
        get_current_pads().api.log_mem_artifact(name, obj, write_format=write_format, description=description,
                                                path=path, meta=meta)

    @staticmethod
    def store_tag(key, value, value_format="string", description="", meta: dict = None):
        """
        Set a tag for your current run.
        :param meta: Meta information you want to store about the parameter. This is an extension by pypads creating a
        json containing some meta information.
        :param value_format: Format of the value held in tag
        :param description: Description what this tag indicates
        :param key: Tag key
        :param value: Tag value
        :return:
        """
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        # consolidated_json = pads.cache.get('consolidated_dict', None)
        # if consolidated_json is not None:
        #     tags = consolidated_json.get('tags', dict())
        #     tags[meta.name] = val
        #     consolidated_json['tags'] = tags
        #     pads.cache.add('consolidated_json', consolidated_json)
        pads.api.set_tag(key, value, value_format=value_format, description=description, meta=meta)

    def _base_path(self):
        return os.path.join(self.tracked_by.created_by, "TrackedObjects", self.__class__.__name__)

    def _get_artifact_path(self, name):
        return os.path.join(str(id(self)), name)

    def store(self, output, key="tracked_object", *json_path):
        """
        :param output:
        :param key: Name of the tracking object in the schema
        :param json_path: path in the output schema
        :return:
        """
        output.add_tracked_object(self, key, *json_path)


class LoggerOutput(ProvenanceMixin):

    def __init__(self, _pypads_env, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._envs = [_pypads_env]

    def add_call_env(self, _pypads_env: LoggerEnv):
        self._envs.append(_pypads_env)

    @property
    def envs(self):
        """
        Stored environments used to produce the output.
        :return:
        """
        return self._envs

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return OutputModel

    def add_tracked_object(self, to: TrackedObject, key, *json_path):
        """
        Add a new tracked object to the logger output. Given json_path is the path to the tracked object
        in the result schema.
        :param to: Tracked object
        :param key: key to place the tracked object at
        :param json_path: path to the tracked object holding dict
        :return:
        """
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
        self.additional_data = dict_merge(*[e.data for e in self._envs])
        from pypads.app.pypads import get_current_pads
        return get_current_pads().api.store_logger_output(self, path)

    def set_failure_state(self, e: Exception):
        self.failed = "Logger Output might be inaccurate/corrupt due to exception in execution: '{}'".format(str(e))


class Logger(BaseDefensiveCallableMixin, IntermediateCallableMixin, DependencyMixin,
             LibrarySpecificMixin, ProvenanceMixin, ConfigurableCallableMixin, metaclass=ABCMeta):
    """
    Generic tracking function used for storing information to a backend.
    """

    is_a: HttpUrl = f"{ontology_uri}tracking-function"

    # Default allow all libraries
    supported_libraries = {LibSelector(name=".*", constraint="*")}
    _schema_path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tracked_objects: Set[TrackedObject] = set()
        self._cleanup_fns = {}

    @classmethod
    def build_output(cls, _pypads_env, **kwargs):
        schema_class = cls.output_schema_class()

        if schema_class:
            class OutputModelHolder(LoggerOutput):

                @classmethod
                def get_model_cls(cls) -> Type[BaseModel]:
                    return schema_class

            return OutputModelHolder(_pypads_env, **kwargs)
        return None

    @classmethod
    def output_schema_class(cls) -> Optional[Type[OutputModel]]:
        return None

    @classmethod
    def output_schema(cls):
        schema_class = cls.output_schema_class()
        if schema_class:
            return schema_class.schema()
        return None

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
            pads = get_current_pads()

            schema_repo = pads.schema_repository

            schema = cls.schema()
            schema_hash = persistent_hash(str(schema))
            if not schema_repo.has_object(uid=schema_hash):
                schema_entity = schema_repo.get_object(uid=schema_hash)
                schema_path = os.path.join(path, cls.get_model_cls().__name__ + "_schema")
                schema_entity.log_mem_artifact(schema_path, schema, write_format=FileFormats.json)
                schema_entity.set_tag("pypads.schema_name", schema["title"], "Name for the schema stored here.")

            schema = cls.output_schema()
            if schema:
                schema_hash = persistent_hash(str(schema))
                if not schema_repo.has_object(uid=schema_hash):
                    schema_entity = schema_repo.get_object(uid=schema_hash)
                    schema_path = os.path.join(path, cls.__name__ + "_output_schema")
                    schema_entity.log_mem_artifact(schema_path, schema, write_format=FileFormats.json)
                    schema_entity.set_tag("pypads.schema_name", schema["title"], "Name for the schema stored here.")

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

    def _call(self, _pypads_env: LoggerEnv, _logger_call: LoggerCall, _logger_output, *args, **kwargs):
        """
        Function where to add you custom code to execute before starting or ending the run.

        :param pads: the current instance of PyPads.
        """
        pass

    def __real_call__(self, *args, _pypads_env: LoggerEnv, **kwargs):
        """
        Function implementing the shared call structure.
        :param args:
        :param _pypads_env:
        :param _pypads_silent: Flag to indicate logs should not be stored.
        :param kwargs:
        :return:
        """
        self.store_schema(self._base_path())

        # parameters passed by the env
        _pypads_params = _pypads_env.parameter

        logger_call = self.build_call_object(_pypads_env, created_by=self.store_schema(self._base_path()))
        output = self.build_output(_pypads_env)

        kwargs_ = {**self.static_parameters, **kwargs}

        try:
            _return, time = self._fn(*args, _pypads_env=_pypads_env, _logger_call=logger_call, _logger_output=output,
                                     _pypads_params=_pypads_params,
                                     **kwargs_)

            logger_call.execution_time = time
        except Exception as e:
            logger_call.failed = str(e)
            if output:
                output.set_failure_state(e)
            raise e
        finally:
            for fn in self.cleanup_fns(logger_call):
                fn(self, logger_call)
            if "_pypads_silent" not in kwargs_ or not kwargs_["_pypads_silent"]:
                if output:
                    logger_call.output = output.store(self._base_path())
                logger_call.store()
        return _return

    @abstractmethod
    def build_call_object(self, _pypads_env, **kwargs):
        raise NotImplementedError()
