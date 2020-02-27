import os

from pypads.test.base_test import BaseTest

from pypadsext.concepts.util import get_by_tag


class PyPadrePadsDecoratorsTest(BaseTest):

    def test_dataset(self):
        """
        This example will track the concepts created by the decorated function
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        tracker = PyPadrePads()
        cwd = os.getcwd()
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
            "Quality"]

        ds_name = "winequality_red"

        @tracker.decorators.dataset(name=ds_name, columns=columns_wine, target=[-1])
        def load_wine():
            import numpy as np
            name = "/winequality-red.csv"
            data = np.loadtxt(cwd + name, delimiter=';', usecols=range(12))
            return data

        data = load_wine()

        # --------------------------- asserts ---------------------------
        import mlflow
        datasets_repo = mlflow.get_experiment_by_name("datasets")
        datasets = get_by_tag("pypads.dataset", experiment_id=datasets_repo.experiment_id)

        def get_name(run):
            tags = run.data.tags
            return tags.get("pypads.dataset", None)

        ds_names = [get_name(ds) for ds in datasets]
        assert ds_name in ds_names

        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads

    def test_custom_splitter(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        tracker = PyPadrePads()

        @tracker.decorators.dataset(name="iris")
        def load_iris():
            from sklearn.datasets import load_iris
            return load_iris()

        @tracker.decorators.splitter()
        def splitter(data, training=0.6):
            import numpy as np
            idx = np.arange(data.shape[0])
            cut = int(len(idx) * training)
            return idx[:cut], idx[cut:]

        data = load_iris()

        train_idx, test_idx = splitter(data.data, training=0.7)

        # --------------------------- asserts ---------------------------
        import mlflow, numpy
        assert tracker.cache.run_exists("current_split")
        split = tracker.cache.run_get("current_split")
        train, test = (v for k, v in tracker.cache.run_get(split).items())

        assert numpy.array_equal(train_idx, train)
        assert numpy.array_equal(test_idx, test)
        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
        mlflow.end_run()

    def test_default_splitter_with_no_params(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        tracker = PyPadrePads()

        @tracker.decorators.dataset(name="iris")
        def load_iris():
            from sklearn.datasets import load_iris
            return load_iris()

        data = load_iris()

        splits = tracker.actuators.default_splitter(data.data)

        # --------------------------- asserts ---------------------------
        import numpy
        num = -1
        for train_idx, test_idx, val_idx in splits:
            num += 1
            print("train: {}\n test: {}\n val: {}".format(train_idx, test_idx, val_idx))
            assert tracker.cache.run_exists("current_split")
            split = tracker.cache.run_get("current_split")
            assert num == split
            train, test, val = (v for k, v in tracker.cache.run_get(split).items())

            assert numpy.array_equal(train_idx, train)
            assert numpy.array_equal(test_idx, test)
            assert val_idx is None and val is None
        # !-------------------------- asserts ---------------------------

    def test_default_splitter_with_params(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        tracker = PyPadrePads()

        @tracker.decorators.dataset(name="iris")
        def load_iris():
            from sklearn.datasets import load_iris
            return load_iris()

        data = load_iris()

        splits = tracker.actuators.default_splitter(data.data, strategy="cv", n_folds=3, val_ratio=0.2)

        # --------------------------- asserts ---------------------------
        import numpy
        num = -1
        for train_idx, test_idx, val_idx in splits:
            num += 1
            print("train: {}\n test: {}\n val: {}".format(train_idx, test_idx, val_idx))
            assert tracker.cache.run_exists("current_split")
            split = tracker.cache.run_get("current_split")
            assert num == split
            train, test, val = (v for k, v in tracker.cache.run_get(split).items())

            assert numpy.array_equal(train_idx, train)
            assert numpy.array_equal(test_idx, test)
            assert numpy.array_equal(val_idx, val)
        # !-------------------------- asserts ---------------------------

    def test_hyperparameters(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        tracker = PyPadrePads()

        @tracker.decorators.hyperparameters()
        def parameters():
            param1 = 0
            param2 = "test"

        # --------------------------- asserts ---------------------------
        assert tracker.cache.run_exists(parameters.__qualname__)
        params = tracker.cache.run_get(parameters.__qualname__)
        assert "param1" in params.keys() and "param2" in params.keys()
        assert params.get("param1") == 0 and params.get("param2") == "test"
        # !-------------------------- asserts ---------------------------
