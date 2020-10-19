import git
from git import InvalidGitRepositoryError

from pypads.injections.setup.git import IGitRSF
from tests.base_test import BaseTest, TEST_FOLDER, config

GIT_URI = "git://" + TEST_FOLDER


def temporary_folder():
    import tempfile
    temp_dir = tempfile.TemporaryDirectory()
    return temp_dir


class GitBackend(BaseTest):
    """
    This class will test basic functionality of the git backend, e.g, versioning of source code, managing results in a git repo
    """

    def setUp(self) -> None:
        """ Setting up the temporary repository with files to simulate"""
        self.folder = temporary_folder()
        super().setUp()

    def tearDown(self):
        self.folder.cleanup()
        super().tearDown()

    def test_git_setup(self):
        """
        This example will test the versioning of source code.
        :return:
        """
        # Activate tracking of pypads
        from pypads.app.base import PyPads

        # Mocking mlflow source and pypads cwd path extraction
        def cwd():
            return self.folder.name

        import sys, os
        orig_arg = sys.argv[0]
        sys.argv[0] = self.folder.name
        orig_cwd = os.getcwd
        os.getcwd = cwd

        # --------------------------- asserts ------------------------------
        with self.assertRaises(InvalidGitRepositoryError):
            git.Repo(path=self.folder.name)

        tracker = PyPads(uri=TEST_FOLDER, config=config, setup_fns=[IGitRSF()], autostart=True)

        self.assertIsNotNone(git.Repo(self.folder.name))
        temp_repo = git.Repo(self.folder.name)
        # restoring mocked variables
        sys.argv[0] = orig_arg
        os.getcwd = orig_cwd

        self.assertEqual(tracker.results.get_run().tags)

        # !-------------------------- asserts ---------------------------

    def test_git_repository_init(self):
        """

        :return:
        """

    def test_preserving_changes(self):
        """

        :return:
        """

    def test_results_repository(self):
        """

        :return:
        """
