import os

from pypads.test.sklearn.base_sklearn_test import BaseSklearnTest, sklearn_pipeline_experiment, \
    sklearn_simple_decision_tree_experiment
from pypads.test.sklearn.mappings.test_mapping_sklearn import _get_mapping

sklearn_padre = _get_mapping(os.path.join(os.path.dirname(__file__), "pypadre", "sklearn_pypadre.json"))


def cross_validation_on_diabetes():
    import numpy as np
    import matplotlib.pyplot as plt

    from sklearn import datasets
    from sklearn.linear_model import LassoCV
    from sklearn.linear_model import Lasso
    from sklearn.model_selection import KFold
    from sklearn.model_selection import GridSearchCV

    X, y = datasets.load_diabetes(return_X_y=True)
    X = X[:150]
    y = y[:150]

    lasso = Lasso(random_state=0, max_iter=10000)
    alphas = np.logspace(-4, -0.5, 30)

    tuned_parameters = [{'alpha': alphas}]
    n_folds = 5

    clf = GridSearchCV(lasso, tuned_parameters, cv=n_folds, refit=False)
    clf.fit(X, y)
    scores = clf.cv_results_['mean_test_score']
    scores_std = clf.cv_results_['std_test_score']
    plt.figure().set_size_inches(8, 6)
    plt.semilogx(alphas, scores)

    # plot error lines showing +/- std. errors of the scores
    std_error = scores_std / np.sqrt(n_folds)

    plt.semilogx(alphas, scores + std_error, 'b--')
    plt.semilogx(alphas, scores - std_error, 'b--')

    # alpha=0.2 controls the translucency of the fill color
    plt.fill_between(alphas, scores + std_error, scores - std_error, alpha=0.2)

    plt.ylabel('CV score +/- std error')
    plt.xlabel('alpha')
    plt.axhline(np.max(scores), linestyle='--', color='.5')
    plt.xlim([alphas[0], alphas[-1]])

    # #############################################################################
    # Bonus: how much can you trust the selection of alpha?

    # To answer this question we use the LassoCV object that sets its alpha
    # parameter automatically from the data by internal cross-validation (i.e. it
    # performs cross-validation on the training data it receives).
    # We use external cross-validation to see how much the automatically obtained
    # alphas differ across different cross-validation folds.
    lasso_cv = LassoCV(alphas=alphas, random_state=0, max_iter=10000)
    k_fold = KFold(3)

    print("Answer to the bonus question:",
          "how much can you trust the selection of alpha?")
    print()
    print("Alpha parameters maximising the generalization score on different")
    print("subsets of the data:")
    for k, (train, test) in enumerate(k_fold.split(X, y)):
        lasso_cv.fit(X[train], y[train])
        print("[fold {0}] alpha: {1:.5f}, score: {2:.5f}".
              format(k, lasso_cv.alpha_, lasso_cv.score(X[test], y[test])))
    print()
    print("Answer: Not very much since we obtained different alphas for different")
    print("subsets of the data and moreover, the scores for these alphas differ")
    print("quite substantially.")

    plt.show()


class PyPadrePadsTest(BaseSklearnTest):
    def test_cross_validation(self):
        """
        This example will track the experiment exection with the default configuration.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        config = {"events": {
            "splits": {"on": ["pypads_split"]},
            "metric": {"on": ["pypads_metric"]},
            "doc": {"on": ["pypads_dataset", "pypads_fit", "pypads_transform", "pypads_predict"]}
        },
            "mirror_git": True
        }
        tracker = PyPadrePads(config=config, mapping=sklearn_padre)

        import timeit
        t = timeit.Timer(cross_validation_on_diabetes)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------

    def test_pipeline(self):
        """
        This example will track the experiment exection with the default configuration.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        tracker = PyPadrePads(mapping=sklearn_padre)

        import timeit
        t = timeit.Timer(sklearn_pipeline_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------

    def test_decision_tree(self):
        """
        This example will track the experiment exection with the default configuration.
        :return:
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        tracker = PyPadrePads(mapping=sklearn_padre)

        import timeit
        t = timeit.Timer(sklearn_simple_decision_tree_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------
