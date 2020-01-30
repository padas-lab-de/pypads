import datetime
import os
import unittest


class PadreAppTest(unittest.TestCase):

    def test_default_logging_extension(self):
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads()
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

        # assert statements
        import mlflow
        run = mlflow.active_run()
        assert tracker._run.info.run_id == run.info.run_id

        n_inputs = 5 + 1 + 6  # number of inputs of DecisionTreeClassifier.fit, LabelEncoder.fit and f1_score
        n_outputs = 1 + 1 + 1 + 1  # number of outputs of fit and predict and score and f1_score
        assert n_inputs + n_outputs == len(tracker._mlf.list_artifacts(run.info.run_id))

        parameters = tracker._mlf.list_artifacts(run.info.run_id, path='../params')
        assert len(parameters) != 0
        assert 'split_quality' in ''.join([p.path for p in parameters])

        metrics = tracker.mlf.list_artifacts(run.info.run_id, path='../metrics')
        assert len(metrics) != 0

        assert 'f1_score' in ''.join([m.path for m in metrics])

        tags = tracker.mlf.list_artifacts(run.info.run_id, path='../tags')
        assert 'pypads.processor' in ''.join([m.path for m in tags])

    def test_simple_parameter_mapping(self):
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(config={"events": {"parameters": {"on": ["pypads_fit"]}}})
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

        # TODO assert len(tracker.mlf.list_artifacts(run.info.run_id)) == 0

        parameters = tracker._mlf.list_artifacts(run.info.run_id, path='../params')
        assert len(parameters) != 0

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
        name = "PredefinedExperiment" + str(datetime.datetime.now().strftime("%d_%b_%Y_%H-%M-%S.%f"))
        mlflow.set_tracking_uri(os.path.expanduser('~/.mlruns/'))
        experiment_id = mlflow.create_experiment(name)
        try:
            run = mlflow.start_run(experiment_id=experiment_id)
        except Exception:
            # TODO broken when all tests are running. Other tests seem to leave run open
            mlflow.end_run(mlflow.active_run())
            run = mlflow.start_run(experiment_id=experiment_id)
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

        #assert statements
        assert run == tracker._run
        assert name == tracker._experiment.name

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
        tracker = PyPads()
        from sklearn import datasets
        from sklearn.tree import DecisionTreeClassifier

        # load the iris datasets
        dataset = datasets.load_iris()

        # fit a model to the data
        model = DecisionTreeClassifier()
        model.fit(dataset.data, dataset.target)
        model.fit(dataset.data, dataset.target)

        n_inputs = 5*2  # number of inputs of DecisionTreeClassifier.fit
        n_outputs = 1*2  # number of outputs of fit
        run = tracker._run
        # TODO currently a function is only tracked on the first call. Fixed
        # TODO assert n_inputs + n_outputs == len(tracker._mlf.list_artifacts(run.info.run_id))

    def test_keras_base_class(self):
        # Activate tracking of pypads
        from pypads.base import PyPads
        PyPads()
        # first neural network with keras make predictions
        from numpy import loadtxt
        from keras.models import Sequential
        from keras.layers import Dense
        # load the dataset
        import os
        cwd = os.getcwd()
        dataset = loadtxt(cwd + '/keras-diabetes-indians.csv', delimiter=',')

        # split into input (X) and output (y) variables
        X = dataset[:, 0:8]
        y = dataset[:, 8]
        # define the keras model
        model = Sequential()
        model.add(Dense(12, input_dim=8, activation='relu'))
        model.add(Dense(8, activation='relu'))
        model.add(Dense(1, activation='sigmoid'))
        # compile the keras model
        model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
        # fit the keras model on the dataset
        model.fit(X, y, epochs=150, batch_size=10, verbose=0)
        # make class predictions with the model
        predictions = model.predict_classes(X)
        # summarize the first 5 cases
        for i in range(5):
            print('%s => %d (expected %d)' % (X[i].tolist(), predictions[i], y[i]))
