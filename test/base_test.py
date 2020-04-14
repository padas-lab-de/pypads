import unittest


class BaseTest(unittest.TestCase):

    def tearDown(self):
        import mlflow
        if mlflow.active_run():
            # End the mlflow run opened by PyPads
            from pypads.pypads import get_current_pads
            pads = get_current_pads()
            pads.api.end_run()
