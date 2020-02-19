import unittest
import os


class PypadsEXT(unittest.TestCase):

    def test_dataset(self):
        """
        This example will track the dataset created by the decorated function
        """
        # --------------------------- setup of the tracking ---------------------------
        # Activate tracking of pypads
        from pypadre_ext.decorators import PyPadsEXT
        tracker = PyPadsEXT()

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

        @tracker.dataset(name=ds_name, metadata={"attributes": columns_wine, "target": columns_wine[-1]})
        def load_iris():
            from sklearn.datasets import load_iris
            return load_iris()

        data = load_iris()

        # --------------------------- asserts ---------------------------
        import mlflow
        datasets_repo = mlflow.get_experiment_by_name("datasets")
        datasets = tracker.mlf.list_run_infos(datasets_repo.experiment_id)
        
        # !-------------------------- asserts ---------------------------
        # End the mlflow run opened by PyPads
        mlflow.end_run()