from pypads.app.base import DEFAULT_CONFIG
from pypads.app.injections.injection import InjectionLogger
from tests.base_test import TEST_FOLDER, BaseTest


class ConfigsTest(BaseTest):
    def test_recursive_tracking_depth(self):
        """
        In this example, we test the tracking depth of function called recursively
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads

        from pypads.app.base import PyPads

        class TestLogger(InjectionLogger):
            """ Set pre and post bools to true. This is a utility logger for testing purposes. """

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def __post__(self, ctx, *args, _logger_call, _pypads_pre_return, _pypads_result, _args, _kwargs, **kwargs):
                nonlocal call_stack, i
                i += 1
                call_stack.append(_logger_call.original_call.call_id.fn_name)

        test = TestLogger()

        events = {
            "test_logger": test
        }

        hooks = {
            "test_logger": {"on": ["pypads_log"]},
        }
        config = {"mongo_db": False}
        setup_fns = {}
        tracker = PyPads(uri=TEST_FOLDER, config=config, autostart=True,
                         hooks=hooks,
                         events=events,
                         setup_fns=setup_fns)

        @tracker.decorators.track(event=["pypads_log"])
        def dummy1(i):
            print("I am a dummy function")
            return i

        @tracker.decorators.track(event=["pypads_log"])
        def dummy2(i):
            print("I am a dummy function")
            return dummy1(i + 1)

        @tracker.decorators.track(event=["pypads_log"])
        def dummy3(i):
            print("I am a dummy function")
            return dummy2(i - 1)

        # --------------------------- asserts ---------------------------
        i = 0
        call_stack = []
        config["recursion_depth"] = -1
        tracker.config = {**DEFAULT_CONFIG, **config}  # No Limit on tracked recursive calls
        dummy3(2)
        self.assertEqual(3, i)
        self.assertEqual(["dummy1", "dummy2", "dummy3"], call_stack)

        i = 0
        call_stack = []
        config["recursion_depth"] = 0  # Limit tracking to only the first calling function in the stack
        tracker.config = {**DEFAULT_CONFIG, **config}
        dummy3(2)
        self.assertEqual(1, i)
        self.assertEqual(["dummy3"], call_stack)

        i = 0
        call_stack = []
        config[
            "recursion_depth"] = 1  # Limit tracking to only the first and second recursively called function in the stack
        tracker.config = {**DEFAULT_CONFIG, **config}
        dummy3(2)
        self.assertEqual(2, i)
        self.assertEqual(["dummy2", "dummy3"], call_stack)

        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
        tracker.api.end_run()

    def test_recursive_function_tracking(self):
        """
        This example tests the tracking of recursive function
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads

        class TestLogger(InjectionLogger):
            """ Set pre and post bools to true. This is a utility logger for testing purposes. """

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def __post__(self, ctx, *args, _logger_call, _pypads_pre_return, _pypads_result, _args, _kwargs, **kwargs):
                nonlocal i
                i += 1

        test = TestLogger()

        events = {
            "test_logger": test
        }

        hooks = {
            "test_logger": {"on": ["pypads_log"]},
        }
        config = {"mongo_db": False}
        setup_fns = {}
        tracker = PyPads(uri=TEST_FOLDER, config=config, autostart=True,
                         hooks=hooks,
                         events=events,
                         setup_fns=setup_fns, log_level="DEBUG")

        @tracker.decorators.track(event=["pypads_log"])
        def recursive_dummy(s: str):
            if len(s) > 1:
                recursive_dummy(s[:-1])
            else:
                print("I am a dummy recursion")
                return s

        # --------------------------- asserts ---------------------------
        i = 0
        config["recursion_identity"] = True  # Ignoring recursive function calls is enabled
        tracker.config = {**DEFAULT_CONFIG, **config}
        recursive_dummy("".join([str(i) for i in range(1, 10)]))
        self.assertEqual(1, i)

        i = 1
        config["recursion_identity"] = False  # Ignoring recursive function calls is disabled
        tracker.config = {**DEFAULT_CONFIG, **config}
        recursive_dummy("".join([str(i) for i in range(1, 10)]))
        self.assertEqual(10, i)

        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
        tracker.api.end_run()


    def test_double_tracking(self):
        """
        this example tests the case where we have recursive hooking
        :return:
        """
