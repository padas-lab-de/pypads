import unittest


class PypadsHookTest(unittest.TestCase):

    def test_track_param(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads()

        tracker.api.log_param("some_param", 1, meta="{'url': 'https://some.param.url'}")
        tracker.api.end_run()

    def test_track_metric(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads()

        tracker.api.log_metric("some_metric", 1, meta="{'url': 'https://some.param.url'}")
        tracker.api.end_run()

    def test_track_artifact(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads()

        obj = object()

        tracker.api.log_mem_artifact("some_artifact", obj, meta="{'url': 'https://some.atrifact.url'}")
        tracker.api.end_run()
