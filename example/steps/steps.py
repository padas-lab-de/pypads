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
mlflow.end_run()
