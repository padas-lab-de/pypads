from pypads.injections.loggers.mlflow.mlflow_autolog import MlFlowAutoRSF
from pypads.injections.setup.containerize import IContainerizeRSF
from pypads.injections.setup.git import IGitRSF
from pypads.injections.setup.hardware import ISystemRSF, ICpuRSF, IDiskRSF, IPidRSF, ISocketInfoRSF, IRamRSF, \
    IMacAddressRSF
from pypads.injections.setup.misc_setup import DependencyRSF, LoguruRSF, StdOutRSF
from tests.test_sklearn.base_sklearn_test import BaseSklearnTest
from tests.base_test import TEST_FOLDER


class ContainerizeTests(BaseSklearnTest):

    def test_containerize_sklearn_example(self):
        import os
        os.environ["MONGO_DB"] = "pypads"
        os.environ["MONGO_USER"] = "pypads"
        os.environ["MONGO_URL"] = "mongodb://www.padre-lab.eu:2222"
        os.environ["MONGO_PW"] = "8CN7OqknwhYr3RO"

        from pypads.app.base import PyPads
        tracker = PyPads(uri=TEST_FOLDER, config={"events": {"parameters": {"on": ["pypads_fit"]}}}, autostart=True,
                         setup_fns=[MlFlowAutoRSF(), DependencyRSF(), LoguruRSF(), StdOutRSF(), IGitRSF(_pypads_timeout=3),
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
