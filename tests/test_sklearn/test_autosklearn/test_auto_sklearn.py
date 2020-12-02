from tests.base_test import TEST_FOLDER
from tests.test_sklearn.base_sklearn_test import BaseSklearnTest


def autosklearn_digits():
    import autosklearn.classification
    import sklearn.metrics
    from sklearn import datasets
    X, y = datasets.load_digits(return_X_y=True)
    X_train, X_test, y_train, y_test = \
        sklearn.model_selection.train_test_split(X, y, random_state=1)
    automl = autosklearn.classification.AutoSklearnClassifier()
    automl.fit(X_train, y_train)
    y_hat = automl.predict(X_test)
    print("Accuracy score", sklearn.metrics.accuracy_score(y_test, y_hat))


class AutoSklearnTest(BaseSklearnTest):

    def test_pipeline(self):
        """
        This example will track an autosklearn experiment. This will most likely take very long and contain a lot of
        information about tested models with autosklearn. TODO Shouldn't really be a tests and more like an example
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, autostart=True)

        # TODO autosklearn fails we seem to change the _init_ involuntarily
        # import timeit
        # t = timeit.Timer(autosklearn_digits)
        # print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # import mlflow
        # run = mlflow.active_run()
        # assert len(tracker.mlf.list_artifacts(run.info.run_id)) > 0
        # !-------------------------- asserts ---------------------------
        tracker.api.end_run()
