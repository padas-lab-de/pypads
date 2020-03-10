import unittest

import mlflow

from pypads.util import dict_merge


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
class PypadsKerasTest(unittest.TestCase):

    def test_keras_custom_logging(self):
        # --------------------------- setup of the tracking ---------------------------
        global callback
        # custom logging

        def predictions(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
            # Fallback logging function
            global callback
            callback = "predictions"
            return _pypads_callback(*args, **kwargs)

        def keras_predictions(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
                              **kwargs):
            # keras lib logging function
            global callback
            callback = "predictions for keras"
            return _pypads_callback(*args, **kwargs)

        def keras_2_3_1_predictions(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
                                    **kwargs):
            # keras lib logging function
            global callback
            callback = "predictions for keras v 2.3.1"
            return _pypads_callback(*args, **kwargs)

        DEFAULT_Keras_MAPPING = {
            "predictions": predictions,
            ("predictions", "keras"): keras_predictions,
            ("predictions", "keras", "2.3.1"): keras_2_3_1_predictions
        }
        DEFAULT_keras_CONFIG = {"events": {
            "predictions": {"on": ["pypads_predict"]}
        }}

        # Activate tracking of pypads
        from pypads.base import PyPads
        from pypads.base import DEFAULT_LOGGING_FNS, DEFAULT_CONFIG
        PyPads(config=dict_merge(DEFAULT_CONFIG, DEFAULT_keras_CONFIG),
               logging_fns=dict_merge(DEFAULT_LOGGING_FNS, DEFAULT_Keras_MAPPING))

        import timeit
        t = timeit.Timer(keras_simple_sequential_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        assert callback == "predictions for keras v 2.3.1"
        # !-------------------------- asserts ---------------------------
        mlflow.end_run()

    def test_keras_base_class(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        PyPads()

        import timeit
        t = timeit.Timer(keras_simple_sequential_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------
        mlflow.end_run()

    def test_keras_mlp(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        PyPads()

        import timeit
        t = timeit.Timer(keras_mlp_for_multi_class_softmax_classification)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------
        mlflow.end_run()

    def test_keras_autolog(self):
        # Activate tracking of pypads
        from pypads.base import PyPads
        PyPads(config={"events": {
            "autolog": {"on": ["pypads_fit"]},
            "pipeline": {"on": ["pypads_fit", "pypads_predict", "pypads_transform", "pypads_metrics"]}
        }
        })

        import timeit
        t = timeit.Timer(keras_simple_sequential_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------
        mlflow.end_run()
