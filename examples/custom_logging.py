from pathlib import Path

import numpy as np

SEED = 1

from pypadsext.base import PyPadrePads

tracker = PyPadrePads(name="SVC-example")

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


@tracker.decorators.dataset(target=[-1])
def load_wine(type="red"):
    name = "winequality-{}".format(type)
    path = Path(__file__).parent / "{}.csv".format(name)
    data = np.loadtxt(path, delimiter=';', usecols=range(12))
    return data


dataset_ = load_wine()


@tracker.decorators.hyperparameters()
@tracker.decorators.splitter(default=True)
def splitter():
    strategy = "random"
    seed = 0


splits = splitter()

# @tracker.grid_search()
# def parameters():
#     test = {'C': [1.0, 1.5, 2.0], 'kernel': ['rbf'],
#             'gamma': ['auto'],
#             'random_state': [SEED]}
#     return test
#
#
# if not tracker.active_run():
#     tracker.start_run()
#
# for params in parameters():
#     for num, train_idx, test_idx in cv(dataset_, n_folds=5, seed=SEED):
#         model = SVC(probability=True, **params)
#         X_train, y_train = dataset_.features[train_idx], dataset_.targets[train_idx]
#         model.fit(X_train, y_train)
#         X_test = dataset_.features[test_idx]
#         y_test = dataset_.targets[test_idx]
#         predicted = model.predict(X_test)
#         f1_score(y_test, predicted, average="macro")
#         precision_score(y_test, predicted, average="macro")
#         recall_score(y_test, predicted, average="macro")
#     tracker.pop(tracker.run_id())
#     tracker.start_run()
