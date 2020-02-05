import numpy as np
from pathlib import Path

from pypadre.core.model.dataset.dataset import Dataset

from pypads.decorators import split_tracking
from pypads.logging_util import WriteFormats, try_write_artifact

cached_output = {}
SEED = 1


def log_predictions(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
                    write_format=WriteFormats.text,
                    **kwargs):
    result = _pypads_callback(*args, **kwargs)

    for i, sample in enumerate(cached_output.get(str(num)).get('test_indices')):
        cached_output.get(str(num)).get('predictions').get(str(sample)).update({'predicted': result[i]})

    probabilites = None
    if hasattr(self, "predict_proba") or hasattr(self, "_predict_proba"):
        probabilites = self.predict_proba(*args,**kwargs)
    if probabilites is not None:
        for i, sample in enumerate(cached_output.get(str(num)).get('test_indices')):
            cached_output.get(str(num)).get('predictions').get(str(sample)).update({'probabilities': probabilites[i]})

    name = _pypads_context.__name__ + "[" + str(
        id(self)) + "]." + _pypads_wrappe.__name__ + "_results.split_{}".format(num)
    try_write_artifact(name, cached_output.get(str(num)), write_format)
    return result


def dataset_logging(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
                    **kwargs):
    result = _pypads_callback(*args, **kwargs)
    # TODO manage datasets
    return result


config = {"events": {
    "predictions": {"on": ["pypads_predict"], "with": {"write_format": WriteFormats.text.name}},
    "dataset": {"on": ["pypads_load"], "with": {"write_format": WriteFormats.pickle.name}}
}}

mapping = {
    "predictions": log_predictions,
    "dataset": dataset_logging
}
from pypads.base import PyPads

tracker = PyPads(name="SVC", config=config, mapping=mapping)

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


def load_wine(type="white"):
    path = Path(__file__).parent / "winequality-{}.csv".format(type)
    data = np.loadtxt(path, delimiter=';', usecols=range(12))
    return data, columns_wine, columns_wine[-1]


@split_tracking(cache=cached_output)
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
            yield num, train_idx, test_idx

    return splitting_iterator()


data, cols, target = load_wine(type='red')
loader = NumpyLoader()
dataset = loader.load(data, **{"name": "red_winequality",
                               "columns": cols,
                               "target_features": target})


for num, train_idx, test_idx in cv(dataset, n_folds=5, seed=SEED):
    model = SVC(probability=True)

    X_train, y_train = dataset.features()[train_idx], dataset.targets()[train_idx]
    model.fit(X_train, y_train)
    X_test = dataset.features()[test_idx]
    predicted = model.predict(X_test)
    # probabilites = model.predict_proba(X_test)

print(cached_output)
