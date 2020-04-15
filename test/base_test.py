import atexit
import logging
import os
import sys
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
    if os.path.isdir(TEST_FOLDER):
        shutil.rmtree(TEST_FOLDER)
    if hasattr(sys.modules, "sklearn"):
        del sys.modules["sklearn"]
    if hasattr(sys.modules, "pypads"):
        del sys.modules["pypads"]


atexit.register(cleanup)


class BaseTest(unittest.TestCase):

    def setUp(self) -> None:
        if not os.path.isdir(TEST_FOLDER):
            os.mkdir(TEST_FOLDER)

    def tearDown(self):
        from pypads.pypads import current_pads

        if current_pads:
            import mlflow
            if mlflow.active_run():
                # End the mlflow run opened by PyPad
                current_pads.api.end_run()
            # TODO cleanup inbetween tests needed? del sys.modules

            from pypads.autolog.wrapping.module_wrapping import punched_module_names
            for name in punched_module_names:
                if name.split('.')[0] in sys.modules:
                    del sys.modules[name.split('.')[0]]
            # TODO cleanup pypads via a function on pypads itself
            del current_pads


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
