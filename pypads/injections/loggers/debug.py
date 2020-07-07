from pypads import logger

from pypads.app.injections.base_logger import LoggingFunction


class Log(LoggingFunction):
    """
    Function just logging the execution into debug.
    """

    def __pre__(self, ctx, *args, _logger_call, **kwargs):
        logger.debug("Entered " + str(_logger_call.call))

    def __post__(self, ctx, *args, _logger_call, **kwargs):
        logger.debug("Exited " + str(_logger_call.call))


class LogInit(LoggingFunction):
    """
    This function only writes an information of a constructor execution to the stdout.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __pre__(self, ctx, *args, **kwargs):
        logger.info("Pypads tracked class " + str(ctx.__class__) + " initialized.")
