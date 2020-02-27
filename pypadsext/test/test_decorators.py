import os
import unittest

from pypadsext.concepts.util import _get_by_tag


class PyPadrePadsTest(unittest.TestCase):

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
        datasets = _get_by_tag("pypads.dataset", experiment_id=datasets_repo.experiment_id)

        def get_name(run):
            tags = run.data.tags
            return tags.get("pypads.dataset", None)

        ds_names = [get_name(ds) for ds in datasets]
        assert ds_name in ds_names

        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
        mlflow.end_run()

    def test_custom_splitter(self):
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadsext.base import PyPadrePads
        tracker = PyPadrePads()

        @tracker.decorators.dataset(name="iris")
        def load_iris():
            from sklearn.datasets import load_iris
            return load_iris()

        @tracker.decorators.splitter(default=False)
        def splitter(data, training=0.6):
            import numpy as np
            idx = np.arange(data.shape[0])
            cut = int(len(idx) * training)
            return idx[:cut], idx[cut:]

        data = load_iris()

        train_idx, test_idx = splitter(data.data, training=0.7)

        # --------------------------- asserts ---------------------------
        import mlflow
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

        for train_idx, test_idx, val_idx in tracker.actuators.default_splitter(data.data):
            print("train: {}\n test: {}\n val: {}".format(train_idx, test_idx, val_idx))

        # --------------------------- asserts ---------------------------
        import mlflow
        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
        mlflow.end_run()

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

        for train_idx, test_idx, val_idx in tracker.actuators.default_splitter(data.data, strategy="cv", n_folds=3):
            print("train: {}\n test: {}\n val: {}".format(train_idx, test_idx, val_idx))

        # --------------------------- asserts ---------------------------
        import mlflow
        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
        mlflow.end_run()
