from test.base_test import TEST_FOLDER, BaseTest

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
    tracker = PyPads(uri=TEST_FOLDER)
    from test.test_sklearn.base_sklearn_test import sklearn_simple_decision_tree_experiment
    sklearn_simple_decision_tree_experiment(min_samples_leaf=min_samples_leaf)
    tracker.deactivate_tracking(run_atexits=True, reload_modules=False)
    return min_samples_leaf


def parallel_no_tracking(min_samples_leaf=1, dummy=None):
    # --------------------------- setup of the tracking ---------------------------
    from test.test_sklearn.base_sklearn_test import sklearn_simple_decision_tree_experiment
    assert hasattr(dummy, "_pypads_mapping___init__")
    sklearn_simple_decision_tree_experiment(min_samples_leaf=min_samples_leaf)
    return min_samples_leaf


def range_gen(itr=10):
    for i in range(1, itr):
        yield (i,)


def punch_dummy_gen(itr=10):
    from sklearn.decomposition import PCA
    for i in range(1, itr):
        yield (i, PCA())


class ParallelSklearnTest(BaseTest):
    pass

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
        tracker = PyPads(uri=TEST_FOLDER)
        import timeit
        t = timeit.Timer(pool_execution(parallel_no_tracking, punch_dummy_gen()))
        print(t.timeit(1))

    def test_process_execution(self):
        import timeit
        t = timeit.Timer(process_execution(parallel_tracking, range_gen()))
        print(t.timeit(1))

    def test_process_execution_single_tracker(self):
        from pypads.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER)
        import timeit
        t = timeit.Timer(process_execution(parallel_no_tracking, punch_dummy_gen()))
        print(t.timeit(1))

    def test_joblib_execution(self):
        import timeit
        # TODO sklearn pretty print endless loop
        t = timeit.Timer(joblib_execution(parallel_tracking, range_gen()))
        print(t.timeit(1))

    def test_joblib_execution_single_tracker(self):
        from pypads.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER)
        import timeit
        t = timeit.Timer(joblib_execution(parallel_no_tracking, punch_dummy_gen()))
        print(t.timeit(1))
