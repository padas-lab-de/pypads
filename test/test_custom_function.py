import sys

from test.base_test import RanLogger, TEST_FOLDER, BaseTest


def experiment():
    print("I'm an module level experiment")
    return "I'm a return value."


logger = RanLogger()

event_mapping = {
    "ran_logger": logger
}

config = {"events": {
    "ran_logger": {"on": ["pypads_log"]},
},
    "recursion_identity": False,
    "recursion_depth": -1}


class PypadsCustomFunctionTest(BaseTest):

    def test_api(self):
        """
        This example will track the experiment call and default event and context.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, logging_fns=event_mapping)

        tracker.api.track(experiment, ctx=sys.modules[__name__])

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        assert pads.cache.run_exists(id(logger))
        # !-------------------------- asserts ---------------------------

    def test_api_inline(self):
        """
        This example will track the experiment with call and passed event and no context.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, logging_fns=event_mapping)

        def experiment():
            print("I'm an function level experiment")
            return "I'm a return value."

        experiment = tracker.api.track(experiment, events=["pypads_log"])

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        assert pads.cache.run_exists(id(logger))
        # !-------------------------- asserts ---------------------------

    def test_decorator(self):
        """
        This example will track the experiment exection with the default event.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, logging_fns=event_mapping)

        @tracker.decorators.track()
        def experiment():
            print("I'm an function level experiment")
            return "I'm a return value."

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        assert pads.cache.run_exists(id(logger))
        # !-------------------------- asserts ---------------------------

    def test_fit_decorator(self):
        """
        This example will track the experiment exection with passed event.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, logging_fns=event_mapping)

        @tracker.decorators.track(event="pypads_log")
        def experiment():
            print("I'm an function level experiment")
            return "I'm a return value."

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        assert pads.cache.run_exists(id(logger))
        # !-------------------------- asserts ---------------------------

    def test_fail_decorator(self):
        """
        This example will track a failure in a decorated function.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, logging_fns=event_mapping)

        @tracker.decorators.track(event="pypads_log")
        def experiment():
            print("I'm an function level experiment")
            raise Exception("Planed failure")

        # --------------------------- asserts ---------------------------
        with self.assertRaises(Exception):
            experiment()
        # !-------------------------- asserts ---------------------------

    def test_retry(self):
        """
        This example will track a failure and only work on the second run.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, logging_fns=event_mapping)

        i = 0

        @tracker.decorators.track(event="pypads_log")
        def experiment():
            print("I'm an function level experiment")
            nonlocal i
            if i == 0:
                i = i + 1
                raise Exception("Planed failure")
            else:
                return "I'm a retried return value."

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        assert pads.cache.run_exists(id(logger))
        # TODO
        # !-------------------------- asserts ---------------------------
