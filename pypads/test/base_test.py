import unittest


class BaseTest(unittest.TestCase):

    def tearDown(self):
        # End the mlflow run opened by PyPads
        import mlflow
        mlflow.end_run()
