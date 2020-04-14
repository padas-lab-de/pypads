import sys

from test.base_test import BaseTest
from test.order.test_order import First, Second, Third, experiment

event_mapping = {
    "first": First(order=1),
    "second": Second(order=2),
    "third": Third(order=3)
}

config = {"events": {
    "first": {"on": ["order"], "order": 3},
    "second": {"on": ["order"], "order": 2},
    "third": {"on": ["order"], "order": 1},
},
    "recursion_identity": False,
    "recursion_depth": -1}


class PypadsOrderTest(BaseTest):

    def test_order(self):
        """
        This example will track the experiment exection with the default configuration.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(config=config, logging_fns=event_mapping)
        tracker.api.track(experiment, events=["order"], ctx=sys.modules[__name__])

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        assert pads.cache.run_exists(0, 1, 2)
        # !-------------------------- asserts ---------------------------
