from logging import debug, info

from pypads.functions.loggers.base_logger import LoggingFunction
from pypads.logging_util import get_current_call_str


class Log(LoggingFunction):
    """
    Function just logging the execution into debug.
    """

    def __pre__(self, ctx, *args, **kwargs):
        debug("Entered " + get_current_call_str(ctx, kwargs["_pypads_context"], kwargs["_pypads_wrappe"]))

    def __post__(self, ctx, *args, **kwargs):
        debug("Exited " + get_current_call_str(ctx, kwargs["_pypads_context"], kwargs["_pypads_wrappe"]))


class LogInit(LoggingFunction):
    """
    This function only writes an information of a constructor execution to the stdout.
    """

    def __pre__(self, ctx, *args, **kwargs):
        info("Pypads tracked class " + str(ctx.__class__) + " initialized.")
