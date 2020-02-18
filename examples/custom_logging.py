from pathlib import Path

import mlflow
import numpy as np
from pypadre.pod.importing.dataset.dataset_import import NumpyLoader

from pypadre_ext.logging_functions import dataset, predictions
from pypads.logging_util import WriteFormats

cached_output = {}
SEED = 1

config = {"events": {
    "predictions": {"on": ["pypads_predict"], "with": {"write_format": WriteFormats.text.name}},
    "dataset": {"on": ["pypads_load", "pypads_dataset"], "with": {"write_format": WriteFormats.pickle.name}}
}}

mapping = {
    "predictions": predictions,
    "dataset": dataset
}

from pypadre_ext.decorators import PyPadsEXT
tracker = PyPadsEXT(name="SVC", config=config, mapping=mapping)
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


@tracker.dataset(name="Winequality-red", metadata={"attributes": columns_wine,"target": columns_wine[-1]})
def load_wine(type="red"):
    name = "winequality-{}".format(type)
    path = Path(__file__).parent / "{}.csv".format(name)
    data = np.loadtxt(path, delimiter=';', usecols=range(12))
    loader = NumpyLoader()
    dataset = loader.load(data, **{"name": "red_winequality",
                                    "columns": columns_wine,
                                    "target_features": columns_wine[-1]})
    return dataset


dataset_ = load_wine()


@tracker.splitter()
def cv(data, n_folds=3, shuffle=True, seed=None):
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
            yield num, train_idx, test_idx, y[test_idx].reshape(len(test_idx),)

    return splitting_iterator()


@tracker.grid_search()
def grid_search():
    test = {'C': [1.0, 1.5, 2.0], 'kernel': ['rbf'],
            'gamma': ['auto'],
            'random_state': [SEED]}
    return test


if not tracker.active_run():
    tracker.start_run()

for params in grid_search():
    for num, train_idx, test_idx in cv(dataset_, n_folds=5, seed=SEED):
        model = SVC(probability=True, **params)

        X_train, y_train = dataset_.features()[train_idx], dataset_.targets()[train_idx]
        model.fit(X_train, y_train)
        X_test = dataset_.features()[test_idx]
        predicted = model.predict(X_test)
    tracker.pop(tracker.run_id())
    tracker.start_run()
