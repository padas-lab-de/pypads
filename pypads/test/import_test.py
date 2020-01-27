import unittest


class PadreAppTest(unittest.TestCase):

    def test_parameter_logging_extension(self):

        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads()
        from sklearn import datasets
        from sklearn.metrics.classification import f1_score
        # from sklearn.metrics import classification
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
        print(f1_score(expected, predicted, average="macro"))
        # print(metrics.confusion_matrix(expected, predicted))

        # assert statements
        import mlflow
        run = mlflow.active_run()
        assert tracker._run.info.run_id == run.info.run_id

        n_inputs = 5 + 6 # number of inputs of DecisionTreeClassifier.fit and f1_score
        n_outputs = 1 + 1 + 1 # number of outputs of fit and predict and score and f1_score
        assert n_inputs + n_outputs == len(tracker._mlf.list_artifacts(run.info.run_id))

        import urllib
        import os
        parameters = tracker._mlf.list_artifacts(run.info.run_id, path='../params')
        assert len(parameters) != 0
        assert 'split_quality' in ''.join([p.path for p in parameters])
        f = parameters[0]
        path = urllib.parse.urlparse(os.path.join(run.info.artifact_uri, f.path)).path
        if 'split_quality' in path:
            with open(path, 'r') as p:
                param = p.read()
            assert model.criterion == param

    def test_parameter_logging_in_pipelines(self):

        # Activate tracking of pypads
        from pypads.base import PyPads
        PyPads()
        from sklearn import datasets, metrics
        from sklearn.decomposition import PCA
        from sklearn.svm import SVC
        from sklearn.pipeline import Pipeline

        # load the iris dataset
        dataset = datasets.load_iris()

        # define the pipeline
        model = Pipeline([('PCA', PCA()),('SVC', SVC())])
        model.fit(dataset.data, dataset.target)

        #make predictions
        expected = dataset.target
        predicted = model.predict(dataset.data)
        # summarize the fit of the model
        print(metrics.classification_report(expected, predicted))
        print(metrics.confusion_matrix(expected, predicted))

    def test_simple_parameter_mapping(self):
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(config={"events": {"parameters": ["pypads_fit"]}})
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
        assert tracker._run.info.run_id == run.info.run_id

        assert len(tracker.mlf.list_artifacts(run.info.run_id)) == 0

    def test_experiment_configuration(self):
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(name="ConfiguredExperiment")
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
        assert tracker._experiment.name == "ConfiguredExperiment"

    def test_predefined_experiment(self):
        import mlflow
        mlflow.create_experiment("PredefinedExperiment")
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads()
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

    def test_parameter_logging_extension_after_import(self):
        from sklearn import datasets, metrics
        from sklearn.tree import DecisionTreeClassifier
        # TODO global modding fails for unittests but seems to work in production
        # Activate tracking of pypads
        from pypads.base import PyPads
        PyPads(mod_globals=globals())

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

    def test_multiple_fits(self):
        # Activate tracking of pypads
        from pypads.base import PyPads
        PyPads()
        from sklearn import datasets, metrics
        from sklearn.tree import DecisionTreeClassifier

        # load the iris datasets
        dataset = datasets.load_iris()

        # fit a model to the data
        model = DecisionTreeClassifier()
        model.fit(dataset.data, dataset.target)
        model.fit(dataset.data, dataset.target)
        # make predictions
        expected = dataset.target
        predicted = model.predict(dataset.data)
        # summarize the fit of the model
        print(metrics.classification_report(expected, predicted))
        print(metrics.confusion_matrix(expected, predicted))
