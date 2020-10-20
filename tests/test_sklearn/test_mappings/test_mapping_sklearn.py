import os

import mlflow

from pypads.importext.mappings import MappingFile
from tests.base_test import TEST_FOLDER, BaseTest
from tests.test_sklearn.base_sklearn_test import sklearn_pipeline_experiment, sklearn_simple_decision_tree_experiment

minimal = MappingFile(os.path.join(os.path.dirname(__file__), "sklearn_minimal.yml"))
regex = MappingFile(os.path.join(os.path.dirname(__file__), "sklearn_regex.yml"))

config = {
    "include_default_mappings": False
}


class MappingSklearnTest(BaseTest):

    # noinspection DuplicatedCode
    def test_minimal_mapping(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads

        from pypads.injections.setup.misc_setup import DependencyRSF
        set_up_fns = {DependencyRSF()}

        tracker = PyPads(uri=TEST_FOLDER, config=config, mappings=[minimal], autostart=True, setup_fns=set_up_fns)

        import timeit
        t = timeit.Timer(sklearn_pipeline_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        run = mlflow.active_run()
        assert tracker.api.active_run().info.run_id == run.info.run_id
        artifacts = [x for x in tracker.results.get_artifacts(run_id=run.info.run_id)]
        assert len(artifacts) > 0
        # !-------------------------- asserts ---------------------------

    # noinspection DuplicatedCode
    def test_regex_mapping(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.injections.setup.misc_setup import DependencyRSF
        set_up_fns = {DependencyRSF()}
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config=config, mappings=[minimal], autostart=True, setup_fns=set_up_fns)

        import timeit
        t = timeit.Timer(sklearn_simple_decision_tree_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        run = mlflow.active_run()
        assert tracker.api.active_run().info.run_id == run.info.run_id
        artifacts = [x for x in tracker.results.get_artifacts(run_id=run.info.run_id)]
        assert len(artifacts) > 0
        # !-------------------------- asserts ---------------------------
