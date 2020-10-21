import os
import pathlib

from pypads import logger
from pypads.app.misc.mixins import DefensiveCallableMixin, DependencyMixin
from pypads.utils.util import persistent_hash
from git import InvalidGitRepositoryError, GitCommandError, GitError


class ManagedGitFactory(DefensiveCallableMixin, DependencyMixin):
    """
    Class creating a managed git on path. A Managed git is used to interact with a git repository to preserve changes
    by branching etc.
    """

    def __init__(self, pads, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pads = pads

    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        logger.warning("Couldn't initialize git repository because of exception: {0}".format(error))

    _dependencies = {"git"}

    def __real_call__(self, path, *args, **kwargs):
        return ManagedGit(path, pads=self.pads, source=kwargs.get('source', True))


class ManagedGit:
    """
     Managed git on local disk. A Managed git is used to interact with a git repository to preserve changes by
     branching etc.
    """

    def __init__(self, path, pads=None, source=True):
        import git

        if not pads:
            from pypads.app.base import get_current_pads
            self.pads = get_current_pads()
        else:
            self.pads = pads

        # if path is a file we init on the parent directory
        if os.path.isfile(path):
            path = os.path.dirname(path)
        # if path is not representing the source code path
        path = self._verify_path(path, source=source)
        try:
            if not os.path.exists(path):
                pathlib.Path(path).mkdir(parents=True)
            self.repo = git.Repo(path, search_parent_directories=True)
        except InvalidGitRepositoryError:
            logger.warning("No existing git repository was found on {0}, initializing a new one...".format(path))
            self._init_git_repo(path, source=source)

    @property
    def commit_hash(self):
        return self.repo.git.execute(["git", "rev-parse"])

    @property
    def branch(self):
        return self.repo.active_branch.name

    def has_changes(self):
        return len(self.repo.index.diff('HEAD')) > 0 or len(
            self.repo.index.diff(None)) > 0 or len(self.repo.untracked_files) > 0

    def create_patch(self):
        """
        Creates a patch without changing anything on the state of the current repository
        :return: patch, a name for the patch and it's hash
        """
        orig_branch = self.repo.active_branch.name

        # push untracked changes to the stash)
        files = list(
            set([item.a_path for item in self.repo.index.diff('HEAD')]) |
            set([item.a_path for item in self.repo.index.diff(None)]) |
            set(self.repo.untracked_files))
        # files = [item.a_path for item in untracked_files]
        try:
            for f in files:
                self.repo.git.add(f)
            self.repo.git.stash('push', '--keep-index')

            # generate the diff patch
            patch = self.repo.git.stash('show', '-p')
            diff_hash = persistent_hash(patch)
        finally:
            # Remove temporary tracked files
            for f in files:
                self.repo.git.reset(f)
        return patch, diff_hash

    def restore_patch(self, patch):
        """
        Takes a pypads created patch and apply it on the current repository
        :param patch: path to the patch file
        :return:
        """
        try:
            self.repo.git.apply([patch])
        except (GitCommandError, GitError) as e:
            raise Exception(
                "Failed to restore state of the repository from patch file due to exception {}".format(str(e)))

    def _verify_path(self, path, pads=None, source=True):
        """
        Verifies if given path is the correct git repository path.
        :param path:
        :param pads:
        :param source:
        :return:
        """
        # Fix: when using PyPads within a IPython Notebook.
        if path != os.getcwd() and source:
            path = os.getcwd()
            if pads:
                from mlflow.utils.mlflow_tags import MLFLOW_SOURCE_NAME
                pads.api.set_tag(path, MLFLOW_SOURCE_NAME)
        return path

    def _init_git_repo(self, path, source=True):
        """
        Initializes a new git repo if none is found.
        :param path:
        :param source:
        :return:
        """
        import git
        try:
            self.repo = git.Repo.init(path, bare=False)
            self._add_git_ignore()
            if source:
                self.commit_changes(message="Pypads initial commit")
            logger.info("Repository was successfully initialized")
        except (InvalidGitRepositoryError, GitCommandError, GitError) as e:
            raise Exception(
                "No repository was present and git could not initialize a repository in this directory"
                " {0} because of exception: {1}".format(path, e))

    def commit_changes(self, message=""):
        try:
            self.add_untracked_files()
            self._commit(message)
        except Exception as e:
            raise Exception("Failed to commit due to following exception: %s" % str(e))

    def _commit(self, message=""):
        self.repo.git.commit(message=message)

    def add_untracked_files(self):
        untracked_files = self.repo.untracked_files
        if untracked_files and len(untracked_files) > 0:
            self.repo.index.add(untracked_files)
        if len([item.a_path for item in self.repo.index.diff(None)]) > 0:
            self.repo.git.add(A=True)

    def is_remote_empty(self, remote="", remote_url="", init=False):
        from tempfile import TemporaryDirectory
        from git import Repo
        with TemporaryDirectory() as temp_dir:
            repo = Repo.clone_from(remote_url, temp_dir)
            if not repo.branches and init:
                with open(temp_dir + "/Readme.md", "w") as f:
                    f.write("# Results repository")
                repo.git.add(A=True)
                repo.git.commit(message="Initializing the repository with Readme.md")
                repo.git.push(remote, 'master')

    def _add_git_ignore(self):
        try:
            with open(self.repo.working_dir + "/.gitignore", "w") as file:
                file.write(GIT_IGNORE)
            self.repo.git.add(A=True)
        except Exception as e:
            logger.warning("Could add .gitignore file to the repo due to this %s" % str(e))


GIT_IGNORE = """
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
#  Usually these files are written by a python script from a template
#  before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit tests / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
#   For a library or package, you might want to ignore these files since the code is
#   intended to run in multiple environments; otherwise, check them in:
# .python-version

# pipenv
#   According to pypa/pipenv#598, it is recommended to include Pipfile.lock in version control.
#   However, in case of collaboration, if having platform-specific dependencies or dependencies
#   having no cross-platform support, pipenv may install dependencies that don't work, or not
#   install all needed dependencies.
#Pipfile.lock

# PEP 582; used by e.g. github.com/David-OConnor/pyflow
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/
"""
