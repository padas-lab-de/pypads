import os

import mlflow

from pypads.importext.mappings import MappingFile
from test.base_test import TEST_FOLDER, BaseTest
from test.test_sklearn.base_sklearn_test import sklearn_pipeline_experiment, sklearn_simple_decision_tree_experiment

minimal = MappingFile(os.path.join(os.path.dirname(__file__), "sklearn_minimal.yml"))
regex = MappingFile(os.path.join(os.path.dirname(__file__), "sklearn_regex.yml"))


class MappingSklearnTest(BaseTest):

    # noinspection DuplicatedCode
    def test_minimal_mapping(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, mapping=minimal)

        import timeit
        t = timeit.Timer(sklearn_pipeline_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        run = mlflow.active_run()
        assert tracker.api.active_run().info.run_id == run.info.run_id
        assert len(tracker.mlf.list_artifacts(run.info.run_id)) > 0
        # !-------------------------- asserts ---------------------------

    # noinspection DuplicatedCode
    def test_regex_mapping(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, mapping=regex)

        import timeit
        t = timeit.Timer(sklearn_simple_decision_tree_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        run = mlflow.active_run()
        assert tracker.api.active_run().info.run_id == run.info.run_id
        assert len(tracker.mlf.list_artifacts(run.info.run_id)) > 0
        # !-------------------------- asserts ---------------------------
