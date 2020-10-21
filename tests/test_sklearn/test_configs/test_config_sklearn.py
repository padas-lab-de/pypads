from tests.base_test import TEST_FOLDER
from tests.test_sklearn.base_sklearn_test import BaseSklearnTest, sklearn_simple_decision_tree_experiment


class ConfigSklearnTest(BaseSklearnTest):
    def test_depth_limited_tracking(self):
        """
        In this example the LabelEncoder will not be tracked because it is called by the DecisionTreeClassifier
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads

        from pypads.injections.setup.misc_setup import DependencyRSF
        set_up_fns = {DependencyRSF()}

        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config={"recursion_depth": 0}, autostart=True, setup_fns=set_up_fns)

        import timeit
        t = timeit.Timer(sklearn_simple_decision_tree_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        import mlflow
        run = mlflow.active_run()
        assert tracker.api.active_run().info.run_id == run.info.run_id

        # number of inputs of DecisionTreeClassifier.fit
        n_inputs = 5
        n_outputs = 1 + 1  # number of outputs of fit and predict
        assert len(tracker.mlf.list_artifacts(run.info.run_id)) > 0

        parameters = [x for x in tracker.results.get_parameters(run_id=run.info.run_id)]
        # assert len(parameters) != 0
        # assert 'sklearn.tree._classes.DecisionTreeClassifier.max_depth' in ''.join([p.name for p in parameters])

        metrics = [x for x in tracker.results.get_metrics()]
        assert len(metrics) != 0

        assert 'sklearn.metrics.classification.f1_score.' in ''.join([m.name for m in metrics])

        tags = [x for x in tracker.results.get_tags(run_id=run.info.run_id)]
        assert 'pypads.system.processor' in ''.join([m.name for m in tags])

        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
