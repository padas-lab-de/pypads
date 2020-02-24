from pypads.test.sklearn.base_sklearn_test import BaseSklearnTest


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
        This example will track an autosklearn experiment.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads()

        # TODO autosklearn fails we seem to change the _init_ involuntarily
        import timeit
        t = timeit.Timer(autosklearn_digits)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------
