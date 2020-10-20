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
        from pypads.app.pypads import set_current_pads
        from pypads.app.base import PyPads

        tracker = PyPads(uri=TEST_FOLDER, config=config)
        # Mocking get_current_config
        from pypads.app import pypads
        orig_fn = pypads.get_current_config

        def modify_config():
            nonlocal mongo_db
            config = orig_fn()
            config.update({'mongo_db': mongo_db})
            return config

        pypads.get_current_config = modify_config
        # --------------------------- asserts ------------------------------
        # Without MongoSupport
        mongo_db = False
        uri = TEST_FOLDER
        self.assertIsInstance(MLFlowBackendFactory.make(uri), LocalMlFlowBackend)
        self.assertNotIsInstance(MLFlowBackendFactory.make(uri), MongoSupportMixin)

        uri = "http://mlflow.padre-lab.eu"
        self.assertIsInstance(MLFlowBackendFactory.make(uri), RemoteMlFlowBackend)
        self.assertNotIsInstance(MLFlowBackendFactory.make(uri), MongoSupportMixin)

        # With MongoSupport
        mongo_db = True
        uri = TEST_FOLDER
        self.assertIsInstance(MLFlowBackendFactory.make(uri), MongoSupportMixin)

        uri = "http://mlflow.padre-lab.eu"
        self.assertIsInstance(MLFlowBackendFactory.make(uri), MongoSupportMixin)
        pypads.get_current_config = orig_fn
        # !-------------------------- asserts ---------------------------

    def test_MLFlowBackend(self):
        """
        Test the local mlflow backend functionalities.
        :return:
        """
