import sys
import unittest


def experiment():
    print("I'm an module level experiment")
    return "I'm a return value."


def first(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
    from pypads.base import get_current_pads
    pads = get_current_pads()
    print("first")
    pads.cache.run_add(0, True)
    return _pypads_callback(*args, **kwargs)


def second(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
    from pypads.base import get_current_pads
    pads = get_current_pads()
    print("second")
    if not pads.cache.run_exists(0):
        raise ValueError("Not called as second")
    else:
        pads.cache.run_add(1, True)
        return _pypads_callback(*args, **kwargs)


def third(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
    from pypads.base import get_current_pads
    pads = get_current_pads()
    print("third")
    if not pads.cache.run_exists(1):
        raise ValueError("Not called as third")
    else:
        return _pypads_callback(*args, **kwargs)


event_mapping = {
    "first": first,
    "second": second,
    "third": third
}

config = {"events": {
    "first": {"on": ["order"], "order": 3},
    "second": {"on": ["order"], "order": 2},
    "third": {"on": ["order"], "order": 1},
},
    "recursion_identity": False,
    "recursion_depth": -1,
    "retry_on_fail": True}


class PypadsOrderTest(unittest.TestCase):

    def test_api(self):
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
        import mlflow
        # TODO
        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
        mlflow.end_run()
