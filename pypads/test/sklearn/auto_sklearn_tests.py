import unittest


def autosklearn_digits():
    import autosklearn.classification
    import sklearn
    from sklearn import metrics
    from sklearn import datasets
    X, y = datasets.load_iris(return_X_y=True)
    X_train, X_test, y_train, y_test = \
        sklearn.model_selection.train_test_split(X, y, random_state=1)
    automl = autosklearn.classification.AutoSklearnClassifier()
    automl.fit(X_train, y_train)
    y_hat = automl.predict(X_test)
    print("Accuracy score", metrics.accuracy_score(y_test, y_hat))


class PypadsHookTest(unittest.TestCase):

    def test_pipeline(self):
        """
        This example will track the experiment exection with the default configuration.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        # from pypads.base import PyPads
        # tracker = PyPads()

        import timeit
        t = timeit.Timer(autosklearn_digits)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        import mlflow
        # TODO
        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
        mlflow.end_run()
