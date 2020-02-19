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


def sklearn_pipeline_experiment():
    import numpy as np

    from sklearn import datasets
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import GridSearchCV

    # Define a pipeline to search for the best combination of PCA truncation
    # and classifier regularization.
    pca = PCA()
    # set the tolerance to a large value to make the example faster
    logistic = LogisticRegression(max_iter=10000, tol=0.1)
    pipe = Pipeline(steps=[('pca', pca), ('logistic', logistic)])

    X_digits, y_digits = datasets.load_digits(return_X_y=True)

    # Parameters of pipelines can be set using ‘__’ separated parameter names:
    param_grid = {
        'pca__n_components': [5, 15, 30, 45, 64],
        'logistic__C': np.logspace(-4, 4, 4),
    }
    search = GridSearchCV(pipe, param_grid, n_jobs=-1)
    search.fit(X_digits, y_digits)
    print("Best parameter (CV score=%0.3f):" % search.best_score_)
    print(search.best_params_)


class PypadsHookTest(unittest.TestCase):

    def test_pipeline(self):
        """
        This example will track the experiment exection with the default configuration.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads()

        import timeit
        t = timeit.Timer(sklearn_pipeline_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        import mlflow
        # TODO
        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
        mlflow.end_run()

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
        tracker = PyPads(config={"recursion_depth": 0})

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
