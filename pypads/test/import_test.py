import unittest


class PadreAppTest(unittest.TestCase):

    def test_logging_extension(self):

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
        # make predictions
        expected = dataset.target
        predicted = model.predict(dataset.data)
        # summarize the fit of the model
        print(metrics.classification_report(expected, predicted))
        print(metrics.confusion_matrix(expected, predicted))

    def test_simple_parameter_mapping(self):
        # Activate tracking of pypads
        from pypads.base import PyPads
        PyPads(config={"events": {"parameters": ["pypads_fit"]}})
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

    def test_experiment_configuration(self):
        # Activate tracking of pypads
        from pypads.base import PyPads
        PyPads(name="ConfiguredExperiment")
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

    def test_predefined_experiment(self):
        import mlflow
        mlflow.create_experiment("PredefinedExperiment")
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

    def test_manual_tag(self):
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
        # make predictions
        expected = dataset.target
        predicted = model.predict(dataset.data)
        import mlflow
        mlflow.set_tag("pypads.custom", id(model))

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
