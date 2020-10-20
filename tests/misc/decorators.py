from tests.base_test import BaseTest, TEST_FOLDER
from tests.injections.injection_loggers import RunLogger

logger = RunLogger()

events = {
    "ran_logger": logger
}

hooks = {
    "ran_logger": {"on": ["pypads_log"]},
}

config = {
    "recursion_identity": False,
    "recursion_depth": -1}


class PyPadsDecorators(BaseTest):

    def test_decorator_default_event(self):
        """
        This example will track the experiment exection with the default event.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, hooks=hooks, events=events, autostart=True)

        @tracker.decorators.track()
        def experiment():
            print("I'm an function level experiment")
            return "I'm a return value."

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        assert pads.cache.run_exists(id(logger))
        # !-------------------------- asserts ---------------------------

    def test_decorator_passed_event(self):
        """
        This example will track the experiment exection with passed event.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, hooks=hooks, events=events, autostart=True)

        @tracker.decorators.track(event="pypads_log")
        def experiment():
            print("I'm an function level experiment")
            return "I'm a return value."

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        assert pads.cache.run_exists(id(logger))
        # !-------------------------- asserts ---------------------------
