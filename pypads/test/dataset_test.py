import unittest

from sklearn import datasets

from pypads.decorators import dataset


class PadreAppTest(unittest.TestCase):

    def test_dataset(self):

        # # Activate tracking of pypads
        # from pypads.autolog.pypads_import import pypads_track
        # pypads_track()

        @dataset()
        def iris():
            return {"name": "iris", "data": datasets.load_iris()}
