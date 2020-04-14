import unittest

from test.sklearn.base_sklearn_test import sklearn_simple_decision_tree_experiment

result_list = []


def log_result(result):
    # This is called whenever foo_pool(i) returns a result.
    # result_list is modified only by the main process, not the pool workers.
    result_list.append(result)


def process_execution(fn, arg_gen):
    import multiprocessing

    def parallelize():
        for arg in arg_gen:
            p = multiprocessing.Process(target=fn, args=arg)
            p.start()
            p.join()

    return parallelize


def pool_execution(fn, arg_gen):
    import multiprocessing

    def parallelize():
        pool = multiprocessing.Pool()
        for arg in arg_gen:
            pool.apply_async(fn, arg, callback=log_result)
        pool.close()
        pool.join()

    return parallelize


def joblib_execution(fn, arg_gen):
    def parallelize():
        from joblib import Parallel
        from joblib import delayed
        Parallel(n_jobs=2, prefer="processes")(delayed(fn)(*i) for i in arg_gen)

    return parallelize


def parallel_tracking(min_samples_leaf=1):
    # --------------------------- setup of the tracking ---------------------------
    # Activate tracking of pypads
    from pypads.base import PyPads
    tracker = PyPads()
    sklearn_simple_decision_tree_experiment(min_samples_leaf=min_samples_leaf)
    tracker.api.end_run()
    return min_samples_leaf


def parallel_no_tracking(min_samples_leaf=1, dummy=None):
    # --------------------------- setup of the tracking ---------------------------
    assert hasattr(dummy, "_pypads_wrapped")
    sklearn_simple_decision_tree_experiment(min_samples_leaf=min_samples_leaf)
    return min_samples_leaf


def range_gen(itr=10):
    for i in range(1, itr):
        yield (i,)


def punch_dummy_gen(itr=10):
    from sklearn.decomposition import PCA
    for i in range(1, itr):
        yield (i, PCA())


class ParallelSklearnTest(unittest.TestCase):

    def test_pool_execution(self):
        # TODO fails in run / works in debug for MacOsx
        import timeit
        t = timeit.Timer(pool_execution(parallel_tracking, range_gen()))
        print(t.timeit(1))

        # --------------------------- asserts ---------------------------
        # TODO
        # !-------------------------- asserts ---------------------------

    def test_pool_execution_single_tracker(self):
        from pypads.base import PyPads
        tracker = PyPads()
        import timeit
        t = timeit.Timer(pool_execution(parallel_no_tracking, punch_dummy_gen()))
        print(t.timeit(1))

    def test_process_execution(self):
        import timeit
        t = timeit.Timer(process_execution(parallel_tracking, range_gen()))
        print(t.timeit(1))

    def test_process_execution_single_tracker(self):
        from pypads.base import PyPads
        tracker = PyPads()
        import timeit
        t = timeit.Timer(process_execution(parallel_no_tracking, punch_dummy_gen()))
        print(t.timeit(1))

    def test_joblib_execution(self):
        import timeit
        t = timeit.Timer(joblib_execution(parallel_tracking, range_gen()))
        print(t.timeit(1))

    def test_joblib_execution_single_tracker(self):
        # from pypads.base import PyPads
        # tracker = PyPads()
        from pypads.base import PyPads
        tracker = PyPads(reload_modules=True)
        import timeit
        t = timeit.Timer(joblib_execution(parallel_no_tracking, punch_dummy_gen()))
        print(t.timeit(1))

    def test_punch_after_import(self):
        from test.test_classes.dummy_classes import PunchDummy
        from test.test_classes.dummy_classes import PunchDummy2
        dummy2 = PunchDummy2(2)
        from pypads.base import PyPads
        from test.test_classes.dummy_classes import _get_punch_dummy_mapping
        # TODO PunchDummy2 has PunchDummy as reference
        tracker = PyPads(mapping=_get_punch_dummy_mapping(), reload_modules=True)
        assert PunchDummy._pypads_wrapped
        assert PunchDummy2._pypads_wrapped
        assert dummy2._pypads_wrapped

    def test_punch_sklearn_after_import(self):
        from sklearn.decomposition import PCA
        pca = PCA()
        from sklearn.pipeline import Pipeline
        pipeline = Pipeline(steps=[('pca', pca)])
        from pypads.base import PyPads
        tracker = PyPads(reload_modules=True)
        assert PCA._pypads_wrapped
        assert pca._pypads_wrapped
        assert Pipeline._pypads_wrapped
        assert pipeline._pypads_wrapped
        print(Pipeline._pypads_wrapped)
