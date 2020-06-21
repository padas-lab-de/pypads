import os
import pathlib

from pypads.app.injections.base_logger import LoggingFunction
from pypads.utils.util import dict_merge
from test.base_test import TEST_FOLDER, BaseTest


def keras_simple_sequential_experiment():
    # first neural network with keras make predictions
    from numpy import loadtxt
    from keras.models import Sequential
    from keras.layers import Dense
    # load the dataset
    dataset = loadtxt(os.path.join(pathlib.Path(os.path.abspath(__file__)).parent, 'keras-diabetes-indians.csv'),
                      delimiter=',')

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

    def test_keras_custom_logging(self):
        # --------------------------- setup of the tracking ---------------------------
        global callback
        callback = None

        # custom logging

        class Predictions(LoggingFunction):

            def __pre__(self, ctx, *args, _pypads_env, _args, _kwargs, **kwargs):
                # Fallback logging function
                global callback
                callback = "predictions"

            def __post__(self, ctx, *args, _pypads_env, _pypads_pre_return, _pypads_result, _args, _kwargs,
                         **kwargs):
                pass

        class KerasPredictions(LoggingFunction):

            def __pre__(self, ctx, *args, _pypads_env, _args, _kwargs, **kwargs):
                # Fallback logging function
                global callback
                callback = "predictions for keras"

            def __post__(self, ctx, *args, _pypads_env, _pypads_pre_return, _pypads_result, _args, _kwargs,
                         **kwargs):
                pass

        class Keras231Predictions(LoggingFunction):

            def __pre__(self, ctx, *args, _pypads_env, _args, _kwargs, **kwargs):
                global callback
                callback = "predictions for keras v 2.3.1"

            def __post__(self, ctx, *args, _pypads_env, _pypads_pre_return, _pypads_result, _args, _kwargs,
                         **kwargs):
                pass

        keras_events = {
            "predictions": Predictions(),
            ("predictions", "keras"): KerasPredictions(),
            ("predictions", "keras", "2.3.1"): Keras231Predictions()
        }
        keras_hooks = {
            "predictions": {"on": ["pypads_predict"]}
        }

        # Activate tracking of pypads
        from pypads.app.base import PyPads
        from pypads.bindings.hooks import DEFAULT_HOOK_MAPPING
        from pypads.bindings.events import DEFAULT_LOGGING_FNS
        PyPads(uri=TEST_FOLDER, hooks=dict_merge(DEFAULT_HOOK_MAPPING, keras_hooks),
               events=dict_merge(DEFAULT_LOGGING_FNS, keras_events), autostart=True)

        import timeit
        t = timeit.Timer(keras_simple_sequential_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO add asserts
        assert callback == "predictions for keras v 2.3.1"
        # !-------------------------- asserts ---------------------------

    # @pytest.mark.forked
    def test_keras_base_class(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, autostart=True)

        import timeit
        t = timeit.Timer(keras_simple_sequential_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO add asserts
        # !-------------------------- asserts ---------------------------

    # @pytest.mark.forked
    def test_keras_mlp(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        PyPads(uri=TEST_FOLDER, autostart=True)

        import timeit
        t = timeit.Timer(keras_mlp_for_multi_class_softmax_classification)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO add asserts
        # !-------------------------- asserts ---------------------------

    # @pytest.mark.forked
    def test_keras_autolog(self):
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        PyPads(uri=TEST_FOLDER, hooks={
            "autolog": {"on": ["pypads_fit"]},
            "pipeline": {"on": ["pypads_fit", "pypads_predict", "pypads_transform", "pypads_metrics"]}
        }, autostart=True)

        import timeit
        t = timeit.Timer(keras_simple_sequential_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO add asserts
        # !-------------------------- asserts ---------------------------
