import json
import os
import unittest

from pypads.test.sklearn.base_sklearn_test import sklearn_pipeline_experiment, sklearn_simple_decision_tree_experiment


def _get_mapping(path):
    with open(path) as json_file:
        name = os.path.basename(json_file.name)
        return {name: json.load(json_file)}


minimal = _get_mapping(os.path.join(os.path.dirname(__file__), "sklearn_minimal.json"))
regex = _get_mapping(os.path.join(os.path.dirname(__file__), "sklearn_regex.json"))


class MappingSklearnTest(unittest.TestCase):

    def test_minimal_mapping(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(mapping_file=minimal)

        import timeit
        t = timeit.Timer(sklearn_pipeline_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------

    def test_regex_mapping(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypads.base import PyPads
        tracker = PyPads(mapping_file=regex)

        import timeit
        t = timeit.Timer(sklearn_simple_decision_tree_experiment)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------
