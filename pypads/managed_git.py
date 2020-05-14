import os

from pypads import logger
from pypads.functions.loggers.mixins import DefensiveCallableMixin, DependencyMixin


class ManagedGitFactory(DefensiveCallableMixin, DependencyMixin):

    def __init__(self, pads, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pads = pads

    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        logger.warning("Couldn't initialized git repository because of exception: {0}".format(error))

    @staticmethod
    def _needed_packages():
        return ["git"]

    def __real_call__(self, path, *args, **kwargs):
        return ManagedGit(path, pads=self.pads)


class ManagedGit:

    def __init__(self, path, pads=None):
        import git

        if not pads:
            from pypads.base import get_current_pads
            self.pads = get_current_pads()
        else:
            self.pads = pads

        # if path is a file we init on the parent directory
        if os.path.isfile(path):
            path = os.path.dirname(path)

        from git import InvalidGitRepositoryError
        try:
            self.repo = git.Repo(path, search_parent_directories=True)
        except InvalidGitRepositoryError:
            logger.warning("No existing git repository was found, initializing a new one...")
            self._init_git_repo(path)

    def _init_git_repo(self, path):
        import git
        from git import InvalidGitRepositoryError, GitCommandError, GitError
        try:
            self.repo = git.Repo.init(path, bare=False)
            logger.info("Repository was successfully initialized")
        except (InvalidGitRepositoryError, GitCommandError, GitError) as e:
            raise Exception(
                "No repository was present and git could not initialize a repository in this directory"
                " {0} because of exception: {1}".format(path, e))

    def preserve_changes(self, message=""):
        try:
            orig_branch = self.repo.active_branch.name
            run = self.pads.api.active_run()
            if len(self.repo.index.diff('HEAD')) > 0 or len(
                    self.repo.index.diff(None)) > 0 or self.repo.untracked_files:
                logger.warning("There are uncommitted changes in your git!")
                # Save those changes to stash
                self.repo.git.stash('push', '--include-untracked')

                # check if the changes were already tracked by PyPads
                branch, diff = self.search_tracking_branch(ref=orig_branch)

                if not branch:
                    branch, diff = self.create_tracking_branch(message)
                    logger.info("Created branch " + branch.name)
                    # Log the commit hash, branch and diff
                else:
                    logger.info("Using already existing pypads branch " + branch.name)

                # checkout to the original branch
                self.repo.git.checkout(orig_branch)

                # and pop the stash
                self.repo.git.stash('pop')
            else:
                branch = orig_branch
                diff = None
            return branch, diff
        except Exception as e:
            raise Exception("Preserving commit failed due to %s" % str(e))

    def search_tracking_branch(self, ref='HEAD'):
        """
        Compares the current untracked changes to all existing pypads managed branches.
        Returns the branch if we tracked the changes already in it, otherwise None.
        :return:
        """
        # get the branches created by PyPads
        branches = {b.name: b for b in self.repo.branches if "PyPads" in b.name}
        # get the tags saved by PyPads
        tags = [t.tag for t in self.repo.tags if 'PyPads' in t.path]
        try:
            for tag in tags:
                diff = self.repo.git.diff(ref, tag.tag, '--raw')
                if diff == tag.message:
                    return branches.get(tag.tag), self.repo.git.diff(ref, tag.tag)
        except Exception as e:
            logger.warning("Checking existing branches failed due to %s" % str(e))
            return None, None
        return None, None

    def create_tracking_branch(self, message):
        orig_branch = self.repo.active_branch.name
        run = self.pads.api.active_run()
        logger.warning("Stashing, branching out, "
                       "committing, reverting back and unstashing...")
        # branch out, apply the stashed changes and commit
        branch_name = "PyPads/{}".format(run.info.run_id)
        branch = self.repo.git.checkout(orig_branch, b=branch_name)

        self.repo.git.stash('apply')
        self.add_untracked_files()
        self.repo.git.commit(message=message)

        # create the tag with diff for this branch
        diff_raw = self.repo.git.diff('master', '--raw')
        diff = self.repo.git.diff('master')
        # TODO hash diff?
        self.repo.create_tag(path=branch_name, message=diff_raw)
        return branch, diff

    def commit_changes(self, message=""):
        try:
            self.add_untracked_files()
            self._commit(message)
        except Exception as e:
            raise Exception("Failed to commit due to following exception: %s" % str(e))

    def _commit(self, message=""):
        self.repo.git.commit(message=message)
        self.pads.api.set_tag("pypads.source.git.commit", self.repo.head.object.hexsha)
        self.pads.api.set_tag("pypads.git.branch", self.repo.active_branch.name)

    def add_untracked_files(self):
        untracked_files = self.repo.untracked_files
        if untracked_files and len(untracked_files) > 0:
            self.repo.index.add(untracked_files)
        if len([item.a_path for item in self.repo.index.diff(None)]) > 0:
            self.repo.git.add(A=True)


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

# Unit test / coverage reports
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
