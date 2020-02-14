import unittest


def sklearn_simpled_decision_tree_experiment():
    from sklearn import datasets
    from sklearn.metrics.classification import f1_score
    from sklearn.tree import DecisionTreeClassifier

    # load the iris datasets
    dataset = datasets.load_iris()

    # fit a model to the data
    model = DecisionTreeClassifier()
    model.fit(dataset.data, dataset.target)
    # make predictions
    expected = dataset.target
    predicted = model.predict(dataset.data)
    # summarize the fit of the model
    print("Score: " + str(f1_score(expected, predicted, average="macro")))


class PadreAppTest(unittest.TestCase):

    def test_default_tracking(self):
        """
        This example will track the experiment exection with the default configuration.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads()

        import timeit
        t = timeit.Timer(sklearn_simpled_decision_tree_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        import mlflow
        run = mlflow.active_run()
        assert tracker._run.info.run_id == run.info.run_id

        # number of inputs of DecisionTreeClassifier.fit, LabelEncoder.fit
        n_inputs = 5 + 1
        n_outputs = 1 + 1 + 1  # number of outputs of fit and predict
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
        mlflow.end_run()

    def test_depth_limited_tracking(self):
        """
        In this example the LabelEncoder will not be tracked because it is called by the DecisionTreeClassifier
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        from pypads.logging_util import WriteFormats
        tracker = PyPads(config={"events": {
            "parameters": {"on": ["pypads_fit"]},
            "cpu": {"on": ["pypads_fit"]},
            "output": {"on": ["pypads_fit", "pypads_predict"],
                       "with": {"write_format": WriteFormats.text.name}},
            "input": {"on": ["pypads_fit"], "with": {"write_format": WriteFormats.text.name}},
            "metric": {"on": ["pypads_metric"]}
        },
            "recursion_depth": 0})

        import timeit
        t = timeit.Timer(sklearn_simpled_decision_tree_experiment)
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
        mlflow.end_run()
