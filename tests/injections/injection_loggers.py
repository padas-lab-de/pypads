from typing import Optional, Type, Any

from pypads.app.injections.injection import InjectionLogger, MultiInjectionLogger, OutputModifyingMixin
from pypads.model.logger_output import OutputModel
from pypads.app import base
from tests.base_test import BaseTest, TEST_FOLDER


class RanLogger(InjectionLogger):
    """ Adds id of self to cache. This is a utility logger for testing purposes. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._run_count = 0

    def __pre__(self, ctx, *args, _logger_call, _args, _kwargs, **kwargs):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        self._run_count += 1
        pads.cache.run_add(id(self), self._run_count)

    def __post__(self, ctx, *args, _logger_call, _pypads_pre_return, _pypads_result, _args, _kwargs, **kwargs):
        pass


def dummy_function():
    print("I am a dummy function")
    return "I'm a return value"


class dummy_output(OutputModel):
    """
    Dummy output model for testing.
    """
    var: Any = None


# default config
logger = RanLogger()

events = {
    "ran_logger": logger
}

hooks = {
    "ran_logger": {"on": ["pypads_log"]},
}

config = {
    "recursion_identity": False,
    "recursion_depth": -1,
    "mongo_db" : False}


# Disable all setup functions
base.DEFAULT_SETUP_FNS = {}


class PypadsInjectionLoggers(BaseTest):

    def test_injection_logger(self):
        """
        This example will test injection logger functionalities in __pre__ and __post__
        :return:
        """

        # --------------------------- setup of the tracking ---------------------------

        class TestLogger(InjectionLogger):
            """ Set pre and post bools to true. This is a utility logger for testing purposes. """

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.pre = False
                self.post = False

            def __pre__(self, ctx, *args, _logger_call, _logger_output, _args, _kwargs, **kwargs):
                self.pre = True

            def __post__(self, ctx, *args, _logger_call, _pypads_pre_return, _pypads_result, _args, _kwargs, **kwargs):
                self.post = True

        test = TestLogger()

        events = {
            "test_logger": test
        }

        hooks = {
            "test_logger": {"on": ["pypads_log"]},
        }

        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, hooks=hooks, events=events, autostart=True)

        experiment = tracker.api.track(dummy_function, anchors=["pypads_log"])

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        self.assertTrue(test.pre)
        self.assertTrue(test.post)
        # !-------------------------- asserts ---------------------------

    def test_multi_injection_logger(self):
        """
        This example will test multi injection logger functionalities.
        :return:
        """

        # --------------------------- setup of the tracking ---------------------------

        class TestLogger(MultiInjectionLogger):
            """ increase attrs i and j with each call. This is a utility logger for testing purposes. """

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.i = 0

            @classmethod
            def output_schema_class(cls) -> Optional[Type[OutputModel]]:
                return dummy_output

            @staticmethod
            def finalize_output(pads, logger_call, output, *args, **kwargs):
                pass

            def __pre__(self, ctx, *args, _logger_call, _logger_output, _args, _kwargs, **kwargs):
                self.i += 1

            def __post__(self, ctx, *args, _logger_call, _logger_output, _pypads_pre_return, _pypads_result, _args,
                         _kwargs, **kwargs):
                _logger_output.var = self.i

        test = TestLogger()

        events = {
            "test_logger": test
        }

        hooks = {
            "test_logger": {"on": ["pypads_log"]},
        }

        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, hooks=hooks, events=events, autostart=True)

        experiment = tracker.api.track(dummy_function, anchors=["pypads_log"])

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(5))
        # --------------------------- asserts ---------------------------
        self.assertEqual(test.i, 5)
        self.assertTrue(tracker.cache.run_exists(id(test)))

        data = tracker.cache.run_get(id(test))
        logger_call = data.get('logger_call')
        output = data.get('output')
        self.assertEqual(len(logger_call.call_stack), 5)
        self.assertEqual(output.var, 5)
        # !-------------------------- asserts ---------------------------

    def test_output_modifying_logger(self):
        """
        This example will test injection logger modifying output functionalities.
        :return:
        """

        # --------------------------- setup of the tracking ---------------------------

        class TestLogger(OutputModifyingMixin):
            """ increase attrs i and j with each call. This is a utility logger for testing purposes. """

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def __pre__(self, ctx, *args, _logger_call, _logger_output, _args, _kwargs, **kwargs):
                pass

            def __post__(self, ctx, *args, _logger_call, _logger_output, _pypads_pre_return, _pypads_result, _args,
                         _kwargs, **kwargs):
                return "I'm a modified return value"

        test = TestLogger()

        events = {
            "test_logger": test
        }

        hooks = {
            "test_logger": {"on": ["pypads_log"]},
        }

        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, hooks=hooks, events=events, autostart=True)

        experiment = tracker.api.track(dummy_function, anchors=["pypads_log"])

        # --------------------------- asserts ---------------------------
        self.assertNotEqual(experiment(), "I'm a return value")
        self.assertEqual(experiment(), "I'm a modified return value")
        # !-------------------------- asserts ---------------------------

    def test_failed_logging(self):
        """
        This example will track a failure in a decorated function.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, hooks=hooks, events=events, autostart=True)

        def failing_function():
            print("I'm a failing function")
            raise Exception("Planed failure")

        failing_function = tracker.api.track(failing_function, anchors=["pypads_log"])

        # --------------------------- asserts ---------------------------
        with self.assertRaises(Exception):
            failing_function()
        # !-------------------------- asserts ---------------------------

    def test_retry(self):
        """
        This example will track a failure and only work on the second run.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, hooks=hooks, events=events, autostart=True)

        i = 0

        def experiment():
            print("I'm an function level experiment")
            nonlocal i
            if i == 0:
                i = i + 1
                raise Exception("Planed failure")
            else:
                return "I'm a retried return value."

        experiment = tracker.api.track(experiment, anchors=["pypads_log"])

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        assert pads.cache.run_exists(id(logger))
        self.assertEqual(i, 1)
        # TODO add asserts
        # !-------------------------- asserts ---------------------------
