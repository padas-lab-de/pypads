from tests.base_test import BaseTest, TEST_FOLDER, config


class MLFlowBackend(BaseTest):
    """
        This class will test basic functionality of the git backend, e.g, versioning of source code, managing results in a git repo
        """

    def test_MLFlowBackendFactory(self):
        """
        Test pypads mlflow backend factory
        :return:
        """
        from pypads.app.backends.mlflow import MLFlowBackendFactory, LocalMlFlowBackend, \
            MongoSupportMixin, RemoteMlFlowBackend
        from pypads.app.base import PyPads

        tracker = PyPads(uri=TEST_FOLDER, config=config)

        # --------------------------- asserts ------------------------------
        # Without MongoSupport
        tracker.config = {**tracker.config, **{"mongo_db":False}}
        uri = TEST_FOLDER
        self.assertIsInstance(MLFlowBackendFactory.make(uri), LocalMlFlowBackend)
        self.assertNotIsInstance(MLFlowBackendFactory.make(uri), MongoSupportMixin)

        uri = "http://mlflow.padre-lab.eu"
        self.assertIsInstance(MLFlowBackendFactory.make(uri), RemoteMlFlowBackend)
        self.assertNotIsInstance(MLFlowBackendFactory.make(uri), MongoSupportMixin)

        # With MongoSupport
        tracker.config = {**tracker.config, **{"mongo_db":True}}
        uri = TEST_FOLDER
        self.assertIsInstance(MLFlowBackendFactory.make(uri), MongoSupportMixin)

        uri = "http://mlflow.padre-lab.eu"
        self.assertIsInstance(MLFlowBackendFactory.make(uri), MongoSupportMixin)
        # !-------------------------- asserts ---------------------------

    def test_MLFlowBackend(self):
        """
        Test the mlflow backend mocked functionalities functionalities.
        :return:
        """

