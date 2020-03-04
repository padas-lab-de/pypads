import os

import mlflow
from pypads.test.base_test import BaseTest
from pypads.test.sklearn.mappings.test_mapping_sklearn import _get_mapping

keras_padre = _get_mapping(os.path.join(os.path.dirname(__file__), "keras_pypadre.json"))


def keras_simple_sequential_experiment():
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


# https://keras.io/getting-started/sequential-model-guide/
def keras_mlp_for_multi_class_softmax_classification():
    import keras
    from keras.models import Sequential
    from keras.layers import Dense, Dropout
    from keras.optimizers import SGD

    # Generate dummy data
    import numpy as np
    x_train = np.random.random((1000, 20))
    y_train = keras.utils.to_categorical(np.random.randint(10, size=(1000, 1)), num_classes=10)
    x_test = np.random.random((100, 20))
    y_test = keras.utils.to_categorical(np.random.randint(10, size=(100, 1)), num_classes=10)

    model = Sequential()
    # Dense(64) is a fully-connected layer with 64 hidden units.
    # in the first layer, you must specify the expected input data shape:
    # here, 20-dimensional vectors.
    model.add(Dense(64, activation='relu', input_dim=20))
    model.add(Dropout(0.5))
    model.add(Dense(64, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(10, activation='softmax'))

    sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
    model.compile(loss='categorical_crossentropy',
                  optimizer=sgd,
                  metrics=['accuracy'])

    model.fit(x_train, y_train,
              epochs=20,
              batch_size=128)
    score = model.evaluate(x_test, y_test, batch_size=128)
    print(score)


# noinspection PyMethodMayBeStatic
class PypadsKerasTest(BaseTest):

    def test_keras_base_class(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        PyPadrePads(mapping=keras_padre)

        import timeit
        t = timeit.Timer(keras_simple_sequential_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------

    def test_keras_mlp(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        PyPadrePads(mapping=keras_padre)

        import timeit
        t = timeit.Timer(keras_mlp_for_multi_class_softmax_classification)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------

    def test_keras_autolog(self):
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        PyPadrePads(config={"events": {
            "autolog": {"on": ["pypads_fit"]},
            "pipeline": {"on": ["pypads_fit", "pypads_predict", "pypads_transform", "pypads_metrics"]}
        }
        }, mapping=keras_padre)

        import timeit
        t = timeit.Timer(keras_simple_sequential_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------
