import sys

from loguru import logger as log

logger = log


class LoggerManager:
    """
    Class to manage loguru handlers for pypads. Loguru doesn't give an extensive api to query already existing loggers
    and therefore we need to manage a history ourselves. Thus to joblib and other parallel processes need us to clear
    the loggers out of the locals before returning we also allow for temporarily deleting loggers.
    """

    def __init__(self):
        # remove preconfigured handler
        try:
            logger.remove(0)
        except Exception as e:
            logger.warning(e)
        self._add_history = {}
        self._removed = []

    def add_default_logger(self, level="INFO"):
        self.add(sys.stdout, filter="pypads", level=level)
        # TODO make configureable
        # self.add(sys.stderr, filter="pypads", level="INFO")

    def add(self, *args, **kwargs):
        lid = logger.add(*args, **kwargs)
        self._add_history[lid] = (args, kwargs)
        return lid

    def temporary_remove(self):
        for k in list(self._add_history):
            try:
                self.remove(k)
                self._removed.append(k)
            except Exception as e:
                pass

    def add_loggers_from_history(self):
        for k in self._add_history.values():
            try:
                logger.remove(k)
            except Exception as e:
                pass
            self.add(*k[0], **k[1])
            self._removed.remove(k)

    def remove(self, lid=None):
        if lid:
            logger.remove(lid)
            del self._add_history[lid]
        else:
            logger.remove()
            self._add_history = {}


logger_manager = LoggerManager()
