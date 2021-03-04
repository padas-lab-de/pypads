from pypads.injections.setup.containerize import IContainerizeRSF
from pypads.injections.setup.git import IGitRSF
from pypads.injections.setup.hardware import ISystemRSF, ICpuRSF, IDiskRSF, IPidRSF, ISocketInfoRSF, IRamRSF, \
    IMacAddressRSF
from pypads.injections.setup.misc_setup import DependencyRSF, LoguruRSF, StdOutRSF
from tests.base_test import TEST_FOLDER
from tests.test_sklearn.base_sklearn_test import BaseSklearnTest


class ContainerizeTests(BaseSklearnTest):

    def test_containerize_sklearn_example(self):
        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config={"events": {"parameters": {"on": ["pypads_fit"]}}}, autostart=True,
                         setup_fns=[DependencyRSF(), LoguruRSF(), StdOutRSF(), IGitRSF(_pypads_timeout=3),
                                    ISystemRSF(), IRamRSF(), ICpuRSF(), IDiskRSF(), IPidRSF(), ISocketInfoRSF(),
                                    IMacAddressRSF(), IContainerizeRSF()])

        from sklearn import datasets
        from sklearn.metrics import f1_score
        from sklearn.tree import DecisionTreeClassifier

        # load the iris datasets
        dataset = datasets.load_iris()

        # fit a model to the data
        model = DecisionTreeClassifier()
        model.fit(dataset.data, dataset.target)
        # make predictions
        expected = dataset.target
        predicted = model.predict(dataset.data)
        # summarize the fit of the model
        print("Score: " + str(f1_score(expected, predicted, average="macro")))

        tracker.api.end_run()
        # TODO check if files are here
