import sys

from pypads.functions.analysis.call_tracker import LoggingEnv
from pypads.functions.loggers.base_logger import LoggingFunction
from test.base_test import BaseTest


def experiment():
    print("I'm an module level experiment")
    return "I'm a return value."


class First(LoggingFunction):
    def __post__(self, ctx, *args, _pypads_env, _pypads_pre_return, _pypads_result, _args, _kwargs, **kwargs):
        pass

    def __pre__(ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        print("first")
        pads.cache.run_add(0, True)


class Second(LoggingFunction):
    def __post__(self, ctx, *args, _pypads_env, _pypads_pre_return, _pypads_result, _args, _kwargs, **kwargs):
        pass

    def __pre__(ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        print("second")
        if not pads.cache.run_exists(0):
            raise ValueError("Not called as second")
        pads.cache.run_add(1, True)


class Third(LoggingFunction):
    def __post__(self, ctx, *args, _pypads_env, _pypads_pre_return, _pypads_result, _args, _kwargs, **kwargs):
        pass

    def __pre__(ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        print("third")
        if not pads.cache.run_exists(1):
            raise ValueError("Not called as third")
        pads.cache.run_add(2, True)


event_mapping = {
    "first": First(order=3),
    "second": Second(order=2),
    "third": Third(order=1)
}

config = {"events": {
    "first": {"on": ["order"]},
    "second": {"on": ["order"]},
    "third": {"on": ["order"]},
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
