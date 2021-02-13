import datetime

import mlflow

from tests.base_test import TEST_FOLDER
from tests.test_sklearn.base_sklearn_test import BaseSklearnTest, sklearn_simple_decision_tree_experiment, \
    sklearn_pipeline_experiment


class CommonSklearnTest(BaseSklearnTest):

    def test_pipeline(self):
        """
        This example will track the experiment exection with the default configuration.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        set_up_fns = {}

        from pypads.app.base import PyPads
        tracker = PyPads(setup_fns=set_up_fns, log_level="DEBUG")
        tracker.start_track(experiment_name="1. Experiment")

        import timeit
        t = timeit.Timer(sklearn_pipeline_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        run = mlflow.active_run()
        assert tracker.api.active_run().info.run_id == run.info.run_id

        # artifacts = [x for x in tracker.results.get_artifacts(run_id=run.info.run_id)]
        # assert len(artifacts) > 0

        tracker.api.end_run()
        # !-------------------------- asserts ---------------------------

    def test_default_tracking(self):
        """
        This example will track the experiment exection with the default configuration.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(autostart=False, log_level="WARNING")
        tracker.start_track(experiment_name="1. Experiment")
        tracker.actuators.set_random_seed(seed=1)

        import timeit
        t = timeit.Timer(sklearn_simple_decision_tree_experiment)
        from pypads import logger
        logger.info(t.timeit(1))

        # --------------------------- asserts ---------------------------
        import mlflow
        run = mlflow.active_run()
        assert tracker.api.active_run().info.run_id == run.info.run_id

        tracker.api.end_run()
        # pr.disable()
        # # after your program ends
        # pr.print_stats(sort="cumtime")
        # !-------------------------- asserts ---------------------------

    def test_simple_parameter_mapping(self):
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(autostart=True)
        from sklearn import datasets, metrics
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
        print(metrics.classification_report(expected, predicted))
        print(metrics.confusion_matrix(expected, predicted))

        # assert statements
        import mlflow
        run = mlflow.active_run()
        assert tracker.api.active_run().info.run_id == run.info.run_id

        # assert len(tracker.mlf.list_artifacts(run.info.run_id)) == 0

        # parameters = [x for x in tracker.results.get_parameters(run_id=run.info.run_id)]
        # assert len(parameters) != 0

        tracker.api.end_run()

    def test_experiment_configuration(self):
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads()
        tracker.start_track(experiment_name="ConfiguredExperiment")
        from sklearn import datasets, metrics
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
        print(metrics.classification_report(expected, predicted))
        # print(metrics.confusion_matrix(expected, predicted))

        # assert statements
        # assert tracker._experiment.regex == "ConfiguredExperiment"
        # TODO add asserts
        tracker.api.end_run()

    def test_predefined_experiment(self):
        import mlflow
        name = "PredefinedExperiment" + str(datetime.datetime.now().strftime("%d_%b_%Y_%H-%M-%S.%f"))
        mlflow.set_tracking_uri(TEST_FOLDER)
        experiment_id = mlflow.create_experiment(name)
        try:
            run = mlflow.start_run(experiment_id=experiment_id)
        except Exception:
            # TODO broken when all tests are running. Other tests seem to leave run open
            mlflow.end_run()
            run = mlflow.start_run(experiment_id=experiment_id)
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, autostart=True)
        from sklearn import datasets, metrics
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
        print(metrics.classification_report(expected, predicted))
        print(metrics.confusion_matrix(expected, predicted))

        # assert statements
        assert run == tracker.api.active_run()
        # assert name == tracker._experiment.regex
        # TODO add asserts
        tracker.api.end_run()

    # def test_parameter_logging_extension_after_import(self):
    #     from sklearn import datasets, metrics
    #     from sklearn.tree import DecisionTreeClassifier
    #     # TODO global modding fails for unittests but seems to work in production
    #     # Activate tracking of pypads
    #     from pypads.base import PyPads
    #     PyPads(uri=TEST_FOLDER, reload_modules=True, clear_imports=True)
    #
    #     # load the iris datasets
    #     dataset = datasets.load_iris()
    #
    #     # fit a model to the data
    #     model = DecisionTreeClassifier()
    #     model.fit(dataset.data, dataset.target)
    #     # make predictions
    #     expected = dataset.target
    #     predicted = model.predict(dataset.data)
    #     # summarize the fit of the model
    #     print(metrics.classification_report(expected, predicted))
    #     print(metrics.confusion_matrix(expected, predicted))

    def test_multiple_fits(self):
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, autostart=True)
        from sklearn import datasets
        from sklearn.tree import DecisionTreeClassifier

        # load the iris datasets
        dataset = datasets.load_iris()

        # fit a model to the data
        model = DecisionTreeClassifier()
        model.fit(dataset.data, dataset.target)
        model.fit(dataset.data, dataset.target)

        # TODO add asserts

        tracker.api.end_run()
