import atexit
import logging
import os
import unittest
from os.path import expanduser

from pypads.functions.loggers.base_logger import LoggingFunction
from pypads.pypads import logger

if "loguru" in str(logger):
    import pytest


    @pytest.fixture
    def caplog(_caplog):
        class PropogateHandler(logging.Handler):
            def emit(self, record):
                logging.getLogger(record.name).handle(record)

        from loguru import logger
        handler_id = logger.add(PropogateHandler(), format="{message}")
        yield _caplog
        logger.remove(handler_id)

TEST_FOLDER = os.path.join(expanduser("~"), ".pypads-test")


def cleanup():
    import shutil
    shutil.rmtree(TEST_FOLDER)


atexit.register(cleanup)


class BaseTest(unittest.TestCase):

    def setUp(self) -> None:
        if not os.path.isdir(TEST_FOLDER):
            os.mkdir(TEST_FOLDER)

    def tearDown(self):

        import mlflow
        if mlflow.active_run():
            # End the mlflow run opened by PyPads
            from pypads.pypads import get_current_pads
            pads = get_current_pads()
            pads.api.end_run()


class RanLogger(LoggingFunction):
    """ Adds id of self to cache. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._run_count = 0

    def __pre__(self, ctx, *args, _pypads_env, _args, _kwargs, **kwargs):
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        self._run_count += 1
        pads.cache.run_add(id(self), self._run_count)

    def __post__(self, ctx, *args, _pypads_env, _pypads_pre_return, _pypads_result, _args, _kwargs, **kwargs):
        pass
