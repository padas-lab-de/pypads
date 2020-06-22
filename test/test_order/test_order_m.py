import sys

from test.base_test import BaseTest, TEST_FOLDER
from test.test_order.test_order import First, Second, Third, experiment

events = {
    "ordered_loggers": [First(order=1), Second(order=2), Third(order=3)]
}

hooks = {
    "ordered_loggers": {"on": ["order"]}
}

config = {
    "recursion_identity": False,
    "recursion_depth": -1
}


class PypadsOrderTest(BaseTest):

    def test_order_lf(self):
        """
        This example will track the experiment exection with the default configuration.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, hooks=hooks, events=events, autostart=True)
        tracker.api.track(experiment, anchors=["order"], ctx=sys.modules[__name__])

        import timeit
        t = timeit.Timer(experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        assert pads.cache.run_exists(0, 1, 2)
        # !-------------------------- asserts ---------------------------
