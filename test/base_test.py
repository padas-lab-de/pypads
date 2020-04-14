import unittest


class BaseTest(unittest.TestCase):

    def tearDown(self):
        # End the mlflow run opened by PyPads
        from pypads.pypads import get_current_pads
        pads = get_current_pads()
        pads.api.end_run()
