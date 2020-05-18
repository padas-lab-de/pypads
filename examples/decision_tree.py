"""
===========================================
DecisionTree Classification on Iris dataset
===========================================
An example of using PyPads to track different functions and classes used in a minimal classification examples.
"""
from pypads import logger
from pypads.base import PyPads

tracker = PyPads(uri="git://Users/weissger/.pypads/results11")
tracker.add_result_remote("fim-gitlab", "git@git.fim.uni-passau.de:weissger/pypads-results-test.git")

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
logger.error("Score: " + str(f1_score(expected, predicted, average="macro")))
