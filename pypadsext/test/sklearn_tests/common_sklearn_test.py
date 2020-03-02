import os

from pypads.test.sklearn.base_sklearn_test import BaseSklearnTest, sklearn_pipeline_experiment, \
    sklearn_simple_decision_tree_experiment
from pypads.test.sklearn.mappings.mapping_sklearn_test import _get_mapping

sklearn_padre = _get_mapping(os.path.join(os.path.dirname(__file__), "pypadre", "sklearn_pypadre.json"))


class PyPadrePadsTest(BaseSklearnTest):
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
