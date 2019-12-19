import unittest


class PadreAppTest(unittest.TestCase):

    def test_parameter_logging_extension(self):

        # Activate tracking of pypads
        import sys

        from pypads.autolog.pypads_import import pypads_track
        pypads_track()
        from sklearn import datasets, metrics
        from sklearn.tree import DecisionTreeClassifier

        # load the iris datasets
        dataset = datasets.load_iris()

        # fit a CART model to the data
        model = DecisionTreeClassifier()
        model.fit(dataset.data, dataset.target)
        # make predictions
        expected = dataset.target
        predicted = model.predict(dataset.data)
        # summarize the fit of the model
        print(metrics.classification_report(expected, predicted))
        print(metrics.confusion_matrix(expected, predicted))

    def test(self):
        pass
