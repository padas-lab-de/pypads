import git
from git import InvalidGitRepositoryError

from tests.base_test import BaseTest, TEST_FOLDER, config, TempDir
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

        with TempDir(chdr=True) as test_folder:
            tracker = PyPads(uri=self.folder.name, config=config, autostart=True)

            # --------------------------- asserts ------------------------------
            with self.assertRaises(InvalidGitRepositoryError):
                git.Repo(path=test_folder._path)

            managed_git: ManagedGit = tracker.managed_git_factory(test_folder._path)
            temp_repo = git.Repo(test_folder._path)

            self.assertEqual(temp_repo, managed_git.repo)

            tracker.api.end_run()
        # !-------------------------- asserts ---------------------------

    def test_patch_untracked_changes(self):
        """
        This example will test preserving untracked changes in the existing repository pypads will manage
        :return:
        """
        # Activate tracking of pypads
        from pypads.app.base import PyPads
        import os

        with TempDir(chdr=True) as test_folder:
            tracker = PyPads(uri=self.folder.name, config=config, autostart=True)

            init_git: ManagedGit = tracker.managed_git_factory(test_folder._path)
            # add untracked changes to the repository
            with open(os.path.join(test_folder._path, "new_file.txt"), "w") as file:
                file.write("new untracked changes.")
            managed_git: ManagedGit = tracker.managed_git_factory(test_folder._path)

            # --------------------------- asserts ------------------------------
            self.assertTrue(managed_git.has_changes())

            # Create a patch of the current state of the repository
            status = managed_git.repo.git.status()
            patch, patch_hash = managed_git.create_patch()

            # Do some changes
            os.remove(os.path.join(test_folder._path, "new_file.txt"))
            self.assertNotEqual(status, managed_git.repo.git.status())

            # Restore the state
            with TempDir(chdr=False) as patch_folder:
                with open(os.path.join(patch_folder._path, "patch.patch"), "w") as f:
                    f.write(patch)
                managed_git.restore_patch(os.path.join(patch_folder._path, "patch.patch"))
                self.assertEqual(status, managed_git.repo.git.status())

            tracker.api.end_run()
            # !-------------------------- asserts ---------------------------

    def test_results_repository(self):
        """
        This example will test git managed results repository.
        :return:
        """
        # TODO
