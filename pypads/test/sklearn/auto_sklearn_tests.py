import unittest


def autosklearn_digits():
    from autosklearn import regression
    import sklearn.metrics
    from sklearn import datasets
    # X, y = datasets.load_digits(return_X_y=True)
    # X_train, X_test, y_train, y_test = \
    #     sklearn.model_selection.train_test_split(X, y, random_state=1)
    # automl = autosklearn.classification.AutoSklearnClassifier()
    # automl.fit(X_train, y_train)
    # y_hat = automl.predict(X_test)
    # print("Accuracy score", sklearn.metrics.accuracy_score(y_test, y_hat))
    X, y = datasets.load_boston(return_X_y=True)
    feature_types = (['numerical'] * 3) + ['categorical'] + (['numerical'] * 9)
    X_train, X_test, y_train, y_test = \
        sklearn.model_selection.train_test_split(X, y, random_state=1)

    automl = regression.AutoSklearnRegressor(
        time_left_for_this_task=100,
        per_run_time_limit=10,
    )
    automl.fit(X_train, y_train, dataset_name='boston',
               feat_type=feature_types)

    print(automl.show_models())
    predictions = automl.predict(X_test)
    print("R2 score:", sklearn.metrics.r2_score(y_test, predictions))


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
        t = timeit.Timer(autosklearn_digits)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        import mlflow
        # TODO
        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
        mlflow.end_run()
