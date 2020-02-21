import multiprocessing
import unittest

from pypads.test.sklearn.base_sklearn_test import sklearn_simple_decision_tree_experiment

result_list = []


def log_result(result):
    # This is called whenever foo_pool(i) returns a result.
    # result_list is modified only by the main process, not the pool workers.
    result_list.append(result)


def parallel_sklearn_decision_tree():
    pool = multiprocessing.Pool()
    for i in range(10):
        pool.apply_async(parallel_tracking, (i,), callback=log_result)
    pool.close()
    pool.join()
    print(result_list)


def parallel_tracking(min_samples_leaf=1):
    # --------------------------- setup of the tracking ---------------------------
    # Activate tracking of pypads
    from pypads.base import PyPads
    tracker = PyPads()
    sklearn_simple_decision_tree_experiment(min_samples_leaf=min_samples_leaf)
    return min_samples_leaf


class ParallelSklearnTest(unittest.TestCase):

    def test_parallel_execution(self):
        # TODO fails in run / works in debug for MacOsx
        import timeit
        t = timeit.Timer(parallel_sklearn_decision_tree)
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------
