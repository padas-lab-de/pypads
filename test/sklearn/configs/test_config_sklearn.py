from test.sklearn.base_sklearn_test import BaseSklearnTest, sklearn_simple_decision_tree_experiment


class ConfigSklearnTest(BaseSklearnTest):
    def test_depth_limited_tracking(self):
        """
        In this example the LabelEncoder will not be tracked because it is called by the DecisionTreeClassifier
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(config={"recursion_depth": 0})

        import timeit
        t = timeit.Timer(sklearn_simple_decision_tree_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        import mlflow
        run = mlflow.active_run()
        assert tracker._run.info.run_id == run.info.run_id

        # number of inputs of DecisionTreeClassifier.fit
        n_inputs = 5
        n_outputs = 1 + 1  # number of outputs of fit and predict
        assert n_inputs + n_outputs == len(tracker._mlf.list_artifacts(run.info.run_id))

        parameters = tracker._mlf.list_artifacts(run.info.run_id, path='../params')
        assert len(parameters) != 0
        assert 'split_quality' in ''.join([p.path for p in parameters])

        metrics = tracker.mlf.list_artifacts(run.info.run_id, path='../metrics')
        assert len(metrics) != 0

        assert 'f1_score' in ''.join([m.path for m in metrics])

        tags = tracker.mlf.list_artifacts(run.info.run_id, path='../tags')
        assert 'pypads.processor' in ''.join([m.path for m in tags])

        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
