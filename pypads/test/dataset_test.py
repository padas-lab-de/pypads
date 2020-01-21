import unittest

from sklearn import datasets

from pypads.decorators import dataset


class PadreAppTest(unittest.TestCase):

    def test_dataset(self):

        @dataset()
        def iris():
            return {"name": "iris", "data": datasets.load_iris()}
