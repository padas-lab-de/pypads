from typing import Any

from pypads.app.env import LoggerEnv
from pypads.app.injections.run_loggers import RunTeardown, RunSetup
from pypads.app.injections.tracked_object import LoggerCall
from pypads.model.logger_output import OutputModel
from tests.base_test import BaseTest, TEST_FOLDER, config


def dummy_function():
    print("I am a dummy function")
    return "I'm a return value"


class dummy_output(OutputModel):
    """
    Dummy output model for testing.
    """
    var: Any = None


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

        # --------------------------- asserts ---------------------------
        self.assertTrue(flag)
        # !-------------------------- asserts ---------------------------

    def test_run_teardown(self):
        """
        This example will test run teardown logger functionalities in _call which is called on PyPads __init__
        :return:
        """
        flag = False

        class TestLogger(RunTeardown):
            """ Set pre and post bools to true. This is a utility logger for testing purposes. """

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def _call(self, *args, _pypads_env: LoggerEnv, _logger_call: LoggerCall, _logger_output, **kwargs):
                nonlocal flag
                flag = True

        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, autostart=True)

        tracker.api.register_teardown(name= "test_teardown", post_fn=TestLogger())
        # --------------------------- asserts ---------------------------
        self.assertFalse(flag)
        tracker.api.end_run()
        self.assertTrue(flag)
        # !-------------------------- asserts ---------------------------
