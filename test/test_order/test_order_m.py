import sys

from test.base_test import BaseTest, TEST_FOLDER
from test.test_order.test_order import First, Second, Third, experiment

event_mapping = {
    "ordered_loggers": [First(order=3), Second(order=2), Third(order=1)]
}

config = {"events": {
    "ordered_loggers": {"on": ["order"]}
},
    "recursion_identity": False,
    "recursion_depth": -1}


class PypadsOrderTest(BaseTest):

    def test_order_lf(self):
        """
        This example will track the experiment exection with the default configuration.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, logging_fns=event_mapping)
        tracker.api.track(experiment, events=["order"], ctx=sys.modules[__name__])

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        assert pads.cache.run_exists(0, 1, 2)
        # !-------------------------- asserts ---------------------------
