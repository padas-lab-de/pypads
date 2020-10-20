import git
from git import InvalidGitRepositoryError

from pypads.injections.setup.git import IGitRSF
from tests.base_test import BaseTest, TEST_FOLDER, config
from pypads.app.misc.managed_git import ManagedGit

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

    def test_git_repository_init(self):
        """
        This example will test the versioning of source code.
        :return:
        """
        # Activate tracking of pypads
        from pypads.app.base import PyPads

        # Mocking cwd path extraction for source verification
        def cwd():
            return self.folder.name

        import os
        orig_cwd = os.getcwd
        os.getcwd = cwd

        tracker = PyPads(uri=TEST_FOLDER, config=config, autostart=True)

        # --------------------------- asserts ------------------------------
        with self.assertRaises(InvalidGitRepositoryError):
            git.Repo(path=self.folder.name)

        managed_git: ManagedGit = tracker.managed_git_factory(self.folder.name)
        temp_repo = git.Repo(self.folder.name)

        self.assertEqual(temp_repo, managed_git.repo)
        # restoring mocked variables
        os.getcwd = orig_cwd

        tracker.api.end_run()
        # !-------------------------- asserts ---------------------------

    def test_patch_untracked_changes(self):
        """
        This example will test preserving untracked changes in the existing repository pypads will manage
        :return:
        """
        # Activate tracking of pypads
        from pypads.app.base import PyPads

        # Mocking cwd path extraction for source verification
        def cwd():
            return self.folder.name

        import os
        orig_cwd = os.getcwd
        os.getcwd = cwd

        tracker = PyPads(uri=TEST_FOLDER, config=config, autostart=True)

        init_git: ManagedGit = tracker.managed_git_factory(self.folder.name)
        # add untracked changes to the repository
        with open(os.path.join(self.folder.name, "new_file.txt"), "w") as file:
            file.write("new untracked changes.")
        managed_git: ManagedGit = tracker.managed_git_factory(self.folder.name)

        # --------------------------- asserts ------------------------------
        self.assertTrue(managed_git.has_changes())

        # Create a patch of the current state of the repository
        status = managed_git.repo.git.status()
        patch, patch_hash = managed_git.create_patch()
        patch_folder = temporary_folder()
        patch_file = os.path.join(patch_folder.name, "patch.patch")
        with open(patch_file, "w") as f:
            f.write(patch)

        # Do some changes
        os.remove(os.path.join(self.folder.name, "new_file.txt"))
        self.assertNotEqual(status, managed_git.repo.git.status())

        # Restore the state
        managed_git.restore_patch(patch_file)
        self.assertEqual(status, managed_git.repo.git.status())

        # restoring mocked variables
        os.getcwd = orig_cwd
        patch_folder.cleanup()
        tracker.api.end_run()
        # !-------------------------- asserts ---------------------------

    def test_results_repository(self):
        """
        This example will test git managed results repository.
        :return:
        """
        # TODO
