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
        from pypads.pads_loguru import logger_manager
        handler_id = logger_manager.add(PropogateHandler(), format="{message}")
        yield _caplog
        logger_manager.remove(handler_id)

TEST_FOLDER = os.path.join(expanduser("~"), ".pypads-test_" + str(os.getpid()))


def cleanup():
    import shutil
    if os.path.isdir(TEST_FOLDER):
        shutil.rmtree(TEST_FOLDER)


# TODO Is sometimes not run?
atexit.register(cleanup)


def mac_os_disabled(f):
    """
    Function to disable a test when mac os is used
    :param f:
    :return:
    """
    from sys import platform
    if platform == "darwin":
        def disabled(self):
            print(f.__name__ + ' has been disabled on mac osx')

        return disabled
    else:
        return f


class BaseTest(unittest.TestCase):

    def setUp(self) -> None:
        if not os.path.isdir(TEST_FOLDER):
            os.mkdir(TEST_FOLDER)

    def tearDown(self):
        # TODO isn't run on unexpected errors
        from pypads.pypads import current_pads, set_current_pads
        if current_pads:
            current_pads.deactivate_tracking(run_atexits=True, reload_modules=False)
            # noinspection PyTypeChecker
            set_current_pads(None)


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
