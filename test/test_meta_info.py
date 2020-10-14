from pypads.model.logger_output import MetricMetaModel, ParameterMetaModel, ArtifactMetaModel
from pypads.utils.logging_util import FileFormats
from test.base_test import BaseTest, TEST_FOLDER


class PypadsHookTest(BaseTest):

    def test_track_param(self):

        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads

        name = 'networks_shape'
        neural_network_shape = [10, 10, 3]
        description = 'Shape of the fully connected network'
        keys = ['experiment_id', 'run_id', 'category', 'storage_type']

        tracker = PyPads(uri=TEST_FOLDER, autostart=True)
        tracker.api.log_param(key=name, value=str(neural_network_shape), description=description)

        holder = tracker.api.get_programmatic_output()
        meta = ParameterMetaModel(name=name, value_format='str', data=str(neural_network_shape),
                                  description=description, parent=holder, parent_type=holder.storage_type,
                                  produced_by=holder.produced_by, producer_type=holder.producer_type,
                                  part_of=holder.typed_id())

        # --------------------------- asserts ---------------------------
        # Number of retrieved items should be 1
        retrieved_items = [x for x in tracker.results.get_parameters(name='networks_shape', run_id=meta.run_id)]
        assert len(retrieved_items) == 1

        retrieved_items = retrieved_items[0]
        for key in keys:
            assert retrieved_items.dict().get(key) == meta.dict().get(key)
        # !-------------------------- asserts ---------------------------

    def test_track_metric(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER)
        tracker.activate_tracking()
        tracker.start_track(experiment_name='TEST CASE EXPERIMENT')
        # meta = MetricMetaModel(url='https://some.metric.url', name='some_metric', description='some description',
        #                        step=0)
        tracker.api.log_metric("some_metric", 1)
        tracker.results.get_metrics(name='some_metric')
        artifacts = tracker.results.list_run_infos(experiment_name='TEST CASE EXPERIMENT')
        for artifact in artifacts:
            print(artifact)
        # --------------------------- asserts ---------------------------
        # assert tracker.api.metric_meta("some_metric") == meta.dict()
        # !-------------------------- asserts ---------------------------

    def test_track_mem_artifact(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, autostart=True)

        obj = object()
        tracker.api.log_mem_artifact(path="some_artifact", obj=obj, write_format=FileFormats.pickle,
                                     additional_data=None, holder=None)

        # --------------------------- asserts ---------------------------
        assert tracker.results.load_artifact("some_artifact.pickle", read_format=FileFormats.pickle) is not None
        # !-------------------------- asserts ---------------------------
