import inspect
import time
import traceback
from abc import abstractmethod, ABCMeta
from typing import Type, List, Callable, Optional
from uuid import UUID

import mlflow
from pydantic import BaseModel

from pypads import logger
from pypads.app.env import LoggerEnv
from pypads.app.injections.tracked_object import LoggerCall, TrackedObject, LoggerOutput
from pypads.app.misc.mixins import DependencyMixin, DefensiveCallableMixin, TimedCallableMixin, \
    IntermediateCallableMixin, NoCallAllowedError, ConfigurableCallableMixin, LibrarySpecificMixin, \
    FunctionHolderMixin, BaseDefensiveCallableMixin, ResultDependentMixin, CacheDependentMixin
from pypads.importext.versioning import all_libs
from pypads.model.logger_model import LoggerModel
from pypads.model.logger_output import OutputModel
from pypads.model.metadata import ModelObject
from pypads.model.mixins import ProvenanceMixin, get_library_descriptor
from pypads.utils.logging_util import jsonable_encoder
from pypads.utils.util import persistent_hash


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
            raise error from error
        except NotImplementedError:

            # Ignore if only pre or post where defined
            return None, 0
        except (NoCallAllowedError, PassThroughException) as e:

            # Pass No Call Allowed Error through
            raise e from e
        except Exception as e:

            # Catch other exceptions for this single logger
            try:
                # Failure at timestamp
                # TODO Failure list mlflow.get_run(run_id=_pypads_env.run_id).tags
                mlflow.set_tag(f"pypads.failure.{kwargs['_logger_call'].creator.name}.{str(time.time())}",
                               str(error))
            except Exception as e:
                pass
            logger.error(
                f"Tracking failed for {str(_pypads_env)} with: {str(error)} \nTrace:\n{traceback.format_exc()}")
            return None, 0


class DummyLogger(ProvenanceMixin, ModelObject):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "API Call"
        self.uid = UUID('urn:uuid:00000000-0000-0000-0000-000000000000')
        self.supported_libraries = [all_libs]
        self.schema_location = "Unknown"  # An api call can't store anything about it's result schema because
        # calls currently don't define result schemata

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return LoggerModel


dummy_logger = DummyLogger()


class Logger(BaseDefensiveCallableMixin, IntermediateCallableMixin, CacheDependentMixin, ResultDependentMixin,
             DependencyMixin,
             LibrarySpecificMixin, ProvenanceMixin, ConfigurableCallableMixin, metaclass=ABCMeta):
    """
    Generic tracking function used for storing information to a backend.
    """

    _pypads_stored = None

    # Default allow all libraries
    supported_libraries = {all_libs}
    _schema_path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cleanup_fns = {}
        self.uid = self._persistent_hash()
        self.schema_location = None
        self.identity = self.__class__.__name__

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return LoggerModel

    def build_output(self, _pypads_env, _logger_call, **kwargs):
        schema_class = self.output_schema_class()

        if schema_class:
            class OutputModelHolder(LoggerOutput):

                def __init__(self, _pypads_env, *args, _logger_call=None, **kwargs):
                    super().__init__(_pypads_env, _logger_call=_logger_call,
                                     lib_model=get_library_descriptor(self.get_model_cls()), **kwargs)

                @classmethod
                def get_model_cls(cls) -> Type[BaseModel]:
                    return schema_class

            return OutputModelHolder(_pypads_env, producer=_logger_call, **kwargs)
        return None

    @classmethod
    def output_schema_class(cls) -> Optional[Type[OutputModel]]:
        return OutputModel

    @classmethod
    def output_schema(cls):
        # TODO not needed anymore
        schema_class = cls.output_schema_class()
        if schema_class:
            return schema_class.schema()
        return None

    @classmethod
    def default_output_class(cls, clazz: Type[TrackedObject]) -> Type[OutputModel]:
        class DefaultOutput(OutputModel):
            tracked_object: clazz.get_model_cls() = ...  # Path to tracking objects

            class Config:
                orm_mode = True

        return DefaultOutput

    def cleanup_fns(self, call: LoggerCall) -> List[Callable]:
        return self._cleanup_fns[call] if call in self._cleanup_fns.keys() else []

    def register_cleanup_fn(self, call: LoggerCall, fn):
        if call not in self._cleanup_fns:
            self._cleanup_fns[call] = []
        self._cleanup_fns[call].append(fn)

    def store(self):
        self.store_lib()
        self.schema_location = self.store_schema()

        if not self.__class__._pypads_stored:
            from pypads.app.pypads import get_current_pads
            pads = get_current_pads()
            logger_repo = pads.logger_repository
            if not logger_repo.has_object(uid=self.uid):
                logger_obj = logger_repo.get_object(uid=self.uid)
                logger_obj.log_json(jsonable_encoder(self.dict(force=False, by_alias=True)))
                self.__class__._pypads_stored = self.uid
            else:
                self.__class__._pypads_stored = self.uid
        return self.__class__._pypads_stored

    def get_reference_path(self):
        return self.__class__._pypads_stored

    def _store_results(self, output, logger_call):
        if output:
            logger_call.output = output.store()
        logger_call.finish()
        logger_call.store()

    @classmethod
    def _persistent_hash(cls):
        # TODO include package? version? git hash? content with inspect? Something else?
        return persistent_hash(inspect.getsource(cls))


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

    def _call(self, _pypads_env: LoggerEnv, _logger_call: LoggerCall, _logger_output, _pypads_input_results,
              _pypads_cached_results, *args, **kwargs):
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
        :param kwargs:
        :return:
        """
        kwargs_ = {**self.static_parameters, **kwargs}
        self.store()

        # parameters passed by the env
        _pypads_params = _pypads_env.parameter

        logger_call = self.build_call_object(_pypads_env, creator=self)
        output = self.build_output(_pypads_env, logger_call)

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
            self._store_results(output, logger_call)
        return _return

    @abstractmethod
    def build_call_object(self, _pypads_env, **kwargs):
        raise NotImplementedError()
