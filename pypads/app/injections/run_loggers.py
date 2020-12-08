import traceback
from abc import ABCMeta
from typing import Type

from pydantic.main import BaseModel

# Default init_run fns
from pypads import logger
from pypads.app.env import LoggerEnv
from pypads.app.injections.base_logger import SimpleLogger
from pypads.app.injections.tracked_object import LoggerCall
from pypads.app.misc.mixins import OrderMixin, FunctionHolderMixin, BaseDefensiveCallableMixin
from pypads.exceptions import NoCallAllowedError
from pypads.model.logger_model import RunLoggerModel
from pypads.utils.util import inheritors, persistent_hash, get_experiment_id, get_run_id


class RunLogger(SimpleLogger, OrderMixin, metaclass=ABCMeta):
    category: str = "RunLogger"

    def build_call_object(self, _pypads_env, **kwargs):
        return LoggerCall(logging_env=_pypads_env, category="RunLoggerCall", **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return RunLoggerModel

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
        except (NoCallAllowedError, Exception) as e:
            # do nothing and call the next run function
            logger.error(
                f"Logging failed for {str(self)} with error: {str(error)} \nTrace:\n{traceback.format_exc()}")
            pass


def call_cache(fn, ctx=None):
    """
    translate a logger call to a reference in the cache.
    """

    return "on_import_" + str(id(fn)) if ctx is None else "on_import_" + str(id(fn)) + "_" + str(id(ctx))


class ImportLogger(RunLogger):
    """
    This class should be used to define logging functionalities to be injected on import before pypads wrapping.
    """
    category: str = "ImportLogger"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_call(self, module=None):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        if pads.cache.run_exists("on-import-loggers"):
            call_stack = pads.cache.run_get("on-import-loggers")
        else:
            call_stack = []
        call_stack.append(call_cache(self, module))
        pads.cache.run_add("on-import-loggers", call_stack)

    def end_call(self, module=None):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()

        if pads.cache.run_exists("on-import-loggers"):
            call_stack = pads.cache.run_get("on-import-loggers")
            if call_cache(self, module) in call_stack:
                call_stack.pop(call_cache(self, module))
                pads.cache.run_add("on-import-loggers", call_stack)
            else:
                logger.warning("On-Import call of: " + str(self) + "with context: " + str(module) + "doesn't exist")
        else:
            logger.warning("On-Import call of: " + str(self) + "with context: " + str(module) + "doesn't exist")

    def __real_call__(self, *args, _pypads_env: LoggerEnv = None, module=None, **kwargs):
        logger.debug("Called on Import function " + str(self))
        self.add_call(module=module)
        _return = super().__real_call__(*args, _pypads_env=_pypads_env or LoggerEnv(parameter=dict(),
                                                                                    experiment_id=get_experiment_id(),
                                                                                    run_id=get_run_id(),
                                                                                    data={"category: ImportLogger"}),
                                        **kwargs)
        self.end_call(module=module)
        return _return


class RunSetup(RunLogger, metaclass=ABCMeta):
    """
    This class should be used to define new pre run functions
    """
    category: str = "RunSetupLogger"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __real_call__(self, *args, **kwargs):
        logger.debug("Called pre run function " + str(self))
        return super().__real_call__(*args, **kwargs)


class RunTeardown(RunLogger, metaclass=ABCMeta):
    """
    This class should be used to define new post run functions
    """
    category: str = "RunTeardownLogger"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __real_call__(self, *args, **kwargs):
        logger.debug("Called post run function " + str(self))
        return super().__real_call__(*args, **kwargs)


class SimpleRunFunction(FunctionHolderMixin, BaseDefensiveCallableMixin, OrderMixin):
    """
    This function doesn't represent an own logger and is used to cleanup the job of another logger or setup something.
    """

    def __init__(self, *args, error_message="Some utility function failed.", **kwargs):
        super().__init__(*args, error_message=error_message, **kwargs)


def run_setup_functions():
    """
    Find all pre run functions defined in our imported context.
    :return:
    """
    return inheritors(RunSetup)


def run_teardown_functions():
    """
    Find all post run functions defined in our imported context.
    :return:
    """
    return inheritors(RunTeardown)
