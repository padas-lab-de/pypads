from pypads.model.logger_output import MetricMetaModel, ParameterMetaModel, ArtifactMetaModel
from pypads.utils.logging_util import FileFormats
from test.base_test import BaseTest, TEST_FOLDER


class PypadsHookTest(BaseTest):

    def test_track_param(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, autostart=True)
        meta = ParameterMetaModel(url='https://some.param.url', name='some_param', description='some description',
                                  type='Integer')
        tracker.api.log_param("some_param", 1, meta=meta)

        # --------------------------- asserts ---------------------------
        assert tracker.api.param_meta("some_param") == meta.dict()
        # !-------------------------- asserts ---------------------------

    def test_track_metric(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, autostart=True)
        meta = MetricMetaModel(url='https://some.metric.url', name='some_metric', description='some description',
                               step=0)
        tracker.api.log_metric("some_metric", 1, meta=meta)

        # --------------------------- asserts ---------------------------
        assert tracker.api.metric_meta("some_metric") == meta.dict()
        # !-------------------------- asserts ---------------------------

    def test_track_artifact(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, autostart=True)

        obj = object()
        meta = ArtifactMetaModel(url='https://some.artifact.url', path='some_artifact',
                                 description='some description', format=FileFormats.pickle)
        tracker.api.log_mem_artifact("some_artifact", obj, meta=meta)

        # --------------------------- asserts ---------------------------
        assert tracker.api.artifact_meta("some_artifact").keys() == meta.dict().keys()
        # !-------------------------- asserts ---------------------------
