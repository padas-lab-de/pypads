from test.base_test import BaseTest, TEST_FOLDER


class PypadsHookTest(BaseTest):

    def test_track_param(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, autostart=True)
        meta = "{'url': 'https://some.param.url'}"
        tracker.api.log_param("some_param", 1, meta=meta)

        # --------------------------- asserts ---------------------------
        assert tracker.api.param_meta("some_param")[0] == meta
        # !-------------------------- asserts ---------------------------

    def test_track_metric(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, autostart=True)
        meta = "{'url': 'https://some.metric.url'}"
        tracker.api.log_metric("some_metric", 1, meta=meta)

        # --------------------------- asserts ---------------------------
        assert tracker.api.metric_meta("some_metric")[0] == meta
        # !-------------------------- asserts ---------------------------

    def test_track_artifact(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, autostart=True)

        obj = object()
        meta = "{'url': 'https://some.atrifact.url'}"
        tracker.api.log_mem_artifact("some_artifact", obj, meta=meta)

        # --------------------------- asserts ---------------------------
        assert tracker.api.artifact_meta("some_artifact")[0] == meta
        # !-------------------------- asserts ---------------------------
