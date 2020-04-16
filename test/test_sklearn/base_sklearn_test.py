# ---- Experiments ----

from test.base_test import BaseTest


def sklearn_simple_decision_tree_experiment(min_samples_leaf=1):
    from sklearn import datasets
    from sklearn.metrics.classification import f1_score
    from sklearn.tree import DecisionTreeClassifier

    # load the iris datasets
    dataset = datasets.load_iris()

    # fit a model to the data
    model = DecisionTreeClassifier(min_samples_leaf=min_samples_leaf)
    model.fit(dataset.data, dataset.target)
    # make predictions
    expected = dataset.target
    predicted = model.predict(dataset.data)
    # summarize the fit of the model
    print("Score: " + str(f1_score(expected, predicted, average="macro")))


def sklearn_pipeline_experiment():
    import numpy as np

    from sklearn import datasets
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import GridSearchCV

    # Define a pipeline to search for the best combination of PCA truncation
    # and classifier regularization.
    pca = PCA()
    # set the tolerance to a large value to make the example faster
    logistic = LogisticRegression(max_iter=10000, tol=0.1)
    pipe = Pipeline(steps=[('pca', pca), ('logistic', logistic)])

    X_digits, y_digits = datasets.load_digits(return_X_y=True)

    # Parameters of pipelines can be set using ‘__’ separated parameter names:
    param_grid = {
        'pca__n_components': [5, 15, 30, 45, 64],
        'logistic__C': np.logspace(-4, 4, 4),
    }
    search = GridSearchCV(pipe, param_grid, n_jobs=4)
    search.fit(X_digits, y_digits)
    print("Best parameter (CV score=%0.3f):" % search.best_score_)
    print(search.best_params_)
    search.predict(X_digits)


# !---- Experiments ----

class BaseSklearnTest(BaseTest):

    def setUp(self):
        print("Starting sklearn test...")
        super().setUp()
