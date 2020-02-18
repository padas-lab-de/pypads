from pathlib import Path

import mlflow
import numpy as np

from pypadre_ext.decorators import PyPadsEXT
from pypadre_ext.logging_functions import dataset
from pypads.logging_util import WriteFormats, try_write_artifact

cached_output = {}
SEED = 1


def log_predictions(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
                    write_format=WriteFormats.text,
                    **kwargs):
    result = _pypads_callback(*args, **kwargs)

    run = mlflow.active_run().info.run_id
    for i, sample in enumerate(cached_output.get(run).get(str(num)).get('test_indices')):
        cached_output.get(run).get(str(num)).get('predictions').get(str(sample)).update({'predicted': result[i]})

    probabilities = None
    if hasattr(self, "predict_proba") or hasattr(self, "_predict_proba"):
        probabilities = self.predict_proba(*args, **kwargs)
    if probabilities is not None:
        for i, sample in enumerate(cached_output.get(run).get(str(num)).get('test_indices')):
            cached_output.get(run).get(str(num)).get('predictions').get(str(sample)).update(
                {'probabilities': probabilities[i]})

    name = _pypads_context.__name__ + "[" + str(
        id(self)) + "]." + _pypads_wrappe.__name__ + "_results.split_{}".format(num)
    try_write_artifact(name, cached_output.get(run).get(str(num)), write_format)

    return result


config = {"events": {
    "predictions": {"on": ["pypads_predict"], "with": {"write_format": WriteFormats.text.name}},
    "dataset": {"on": ["pypads_load", "pypads_dataset"], "with": {"write_format": WriteFormats.pickle.name}}
}}

mapping = {
    "predictions": log_predictions,
    "dataset": dataset
}

tracker = PyPadsEXT(name="SVC", config=config, mapping=mapping)
from pypadre.pod.importing.dataset.dataset_import import NumpyLoader
from sklearn.svm import SVC

columns_wine = [
    "Fixed acidity.",
    "Volatile acidity.",
    "Citric acid.",
    "Residual sugar.",
    "Chlorides.",
    "Free sulfur dioxide.",
    "Total sulfur dioxide.",
    "Density.",
    "pH.",
    "Sulphates.",
    "Alcohol.",
    "Quality"
]


# @tracker.dataset(name="Winequality-red", metadata={"attributes": columns_wine,"target": columns_wine[-1]})
# def load_wine(type="red"):
#     name = "winequality-{}".format(type)
#     path = Path(__file__).parent / "{}.csv".format(name)
#     data = np.loadtxt(path, delimiter=';', usecols=range(12))
#     return data


# dataset_ = load_wine()

def load_wine(type="white"):
    name = "winequality-{}".format(type)
    path = Path(__file__).parent / "{}.csv".format(name)
    data = np.loadtxt(path, delimiter=';', usecols=range(12))
    return data, columns_wine, columns_wine[-1]


@tracker.splitter()
def cv(data: Dataset = None, n_folds=3, shuffle=True, seed=None):
    if seed is None:
        seed = 1
    r = np.random.RandomState(seed)
    idx = np.arange(data.size[0])

    def splitting_iterator():
        y = data.targets()
        classes_, y_idx, y_inv, y_counts = np.unique(y, return_counts=True, return_index=True,
                                                     return_inverse=True)
        n_classes = len(y_idx)
        _, class_perm = np.unique(y_idx, return_inverse=True)
        y_encoded = class_perm[y_inv]
        min_groups = np.min(y_counts)
        if np.all(n_folds > y_counts):
            raise ValueError("n_folds=%d cannot be greater than the"
                             " number of members in each class."
                             % (n_folds))
        if n_folds > min_groups:
            raise Warning("The least populated class in y has only %d"
                          " members, which is less than n_splits=%d." % (min_groups, n_folds))
        y_order = np.sort(y_encoded)
        allocation = np.asarray([np.bincount(y_order[i::n_folds], minlength=n_classes)
                                 for i in range(n_folds)])
        test_folds = np.empty(len(y), dtype='i')
        for k in range(n_classes):
            folds_for_class = np.arange(n_folds).repeat(allocation[:, k])
            if shuffle:
                r.shuffle(folds_for_class)
            test_folds[y_encoded == k] = folds_for_class
        num = -1
        for i in range(n_folds):
            num += 1
            test_index = test_folds == i
            train_idx = idx[np.logical_not(test_index)]
            test_idx = idx[test_index]
            yield num, train_idx, test_idx, y[test_idx]

    return splitting_iterator()


data, cols, target = load_wine(type='red')
loader = NumpyLoader()
dataset_ = loader.load(data, **{"name": "red_winequality",
                                "columns": cols,
                                "target_features": target})

# dataset_ = datasets.load_iris()


@tracker.grid_search()
def grid_search(parameters: dict = None):
    import itertools
    master_list = []
    params_list = []
    for params in parameters:
        param = parameters.get(params)
        if not isinstance(param, list):
            param = [param]
        master_list.append(param)
        params_list.append(params)

    grid = itertools.product(*master_list)
    return {'grid': grid, 'parameters': params_list}


test = {'C': [0.5, 1.0, 1.5, 2.0], 'kernel': ['linear', 'rbf', 'poly', 'sigmoid'],
        'gamma': ['auto', 2],
        'random_state': [SEED]}

if not tracker.active_run():
    tracker.start_run()

for params in grid_search(parameters=test):
    for num, train_idx, test_idx in cv(dataset_, n_folds=5, seed=SEED):
        model = SVC(probability=True, **params)

        X_train, y_train = dataset_.features()[train_idx], dataset_.targets()[train_idx]
        model.fit(X_train, y_train)
        X_test = dataset_.features()[test_idx]
        predicted = model.predict(X_test)
        # probabilites = model.predict_proba(X_test)
    run = tracker.run_id()
    cached_output.pop(run, None)
    mlflow.end_run()
    mlflow.start_run(experiment_id=tracker._experiment.experiment_id)

print(cached_output)
