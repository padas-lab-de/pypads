from typing import Optional, Type, Any

from pypads.app.injections.tracked_object import LoggerCall

from pypads.app.env import LoggerEnv

from pypads.app.injections.run_loggers import RunTeardown, SimpleRunFunction, RunSetup
from pypads.model.logger_output import OutputModel
from pypads.app import base
from tests.base_test import BaseTest, TEST_FOLDER


def dummy_function():
    print("I am a dummy function")
    return "I'm a return value"


class dummy_output(OutputModel):
    """
    Dummy output model for testing.
    """
    var: Any = None


config = {
    "recursion_identity": False,
    "recursion_depth": -1,
    "mongo_db": False}

# Disable all setup functions
base.DEFAULT_SETUP_FNS = {}


class PypadsInjectionLoggers(BaseTest):

    def test_run_setup(self):
        """
        This example will test run setup logger functionalities in _call which is called on PyPads __init__
        :return:
        """

        # --------------------------- setup of the tracking ---------------------------

        flag = False

        class TestLogger(RunSetup):
            """ Set pre and post bools to true. This is a utility logger for testing purposes. """

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def _call(self, *args, _pypads_env: LoggerEnv, _logger_call: LoggerCall, _logger_output, **kwargs):
                nonlocal flag
                flag = True

        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, setup_fns=[TestLogger()], autostart=True)

        experiment = tracker.api.track(dummy_function, anchors=["pypads_log"])

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        self.assertTrue(flag)
        # !-------------------------- asserts ---------------------------
