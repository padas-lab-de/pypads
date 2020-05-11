import os

from pypads import logger
from pypads.util import is_package_available


def get_run_git():
    from pypads.pypads import get_current_pads
    from pypads.base import PyPads
    pads: PyPads = get_current_pads()
    run = pads.api.active_run()
    tags = run.data.tags
    source_name = tags.get("mlflow.source.name", None)
    if source_name:
        return get_git_repo(source_name)
    return None


def get_git_repo(path, pads=None):
    if is_package_available("git"):
        import git
        if os.path.isfile(path):
            path = os.path.dirname(path)
            from git import InvalidGitRepositoryError
            try:
                repo = git.Repo(path, search_parent_directories=True)
                check_index(repo, message="PyPads issued commit", pads=pads)
                return repo
            except InvalidGitRepositoryError:
                logger.warning("No existing git repository was found, initializing a new one...")
                return init_git_repo(path, pads=pads)
    else:
        logger.warning("Git needs to be installed to manage a central repository.")
        return None


def init_git_repo(path, pads=None):
    if is_package_available("git"):
        import git
        from git import InvalidGitRepositoryError, GitCommandError, GitError
        try:
            repo = git.Repo.init(path, bare=False)
            add_git_ignore(repo)
            check_index(repo, message="PyPads initialized repository.", init=True, pads=pads)
            logger.info("Repository was successfully initialized")
            return repo
        except (InvalidGitRepositoryError, GitCommandError, GitError):
            logger.warning("Git could not initialize a repository in this directory %s" % path)
            return None
    else:
        logger.warning("Git needs to be installed to manage a central repository.")
        return None


def add_git_ignore(repo):
    try:
        with open(repo.working_dir + "/.gitignore", "w") as file:
            file.write(GIT_IGNORE)
        repo.git.add(A=True)
    except Exception as e:
        logger.warning("Could add .gitignore file to the repo due to this %s" % str(e))


def check_index(repo, message="", init=False, pads=None):
    if not pads:
        from pypads.base import get_current_pads, PyPads
        pads = get_current_pads()
    run = pads.api.active_run()
    if init:
        try:
            add_files(repo)
            repo.git.commit(message=message)
            pads.api.set_tag("pypads.source.git.commit", repo.head.object.hexsha)
            pads.api.set_tag("pypads.git.branch", repo.active_branch.name)

        except Exception as e:
            logger.warning("Could not issue the first commit due to this error %s" % str(e))
    else:
        try:
            orig_branch = repo.active_branch.name
            if len(repo.index.diff('HEAD')) > 0 or len(repo.index.diff(None)) > 0 or repo.untracked_files:
                logger.warning("There are uncommitted changes in your git!")
                # Save those changes to stash
                repo.git.stash('push', '--include-untracked')

                # check if the changes were already tracked by PyPads
                branch, diff = check_existing_branches(repo, ref=orig_branch)

                if not branch:
                    logger.warning("Stashing, branching out, "
                                   "committing, reverting back and unstashing...")
                    # branch out, apply the stashed changes and commit
                    branch = "PyPads/{}".format(run.info.run_id)
                    repo.git.checkout(orig_branch, b=branch)

                    repo.git.stash('apply')
                    add_files(repo)
                    repo.git.commit(message=message)

                    # create the tag with diff for this branch
                    diff_raw = repo.git.diff('master', '--raw')
                    diff = repo.git.diff('master')
                    repo.create_tag(path=branch, message=diff_raw)
                    _hash = repo.head.object.hexsha
                else:
                    logger.warning("Using already existing pypads branch " + branch.name)
                    _hash = branch.object.hexsha
                    branch = branch.name

                # Log the commit hash, branch and diff
                pads.api.set_tag("pypads.git.branch", branch)
                pads.api.set_tag("pypads.source.git.commit", _hash)
                pads.api.set_tag("pypads.source.git.diff", diff)

                # checkout to the master branch
                repo.git.checkout(orig_branch)

                # and pop the stash
                repo.git.stash('pop')

            else:
                pads.api.set_tag("pypads.git.branch", orig_branch)
                pads.api.set_tag("pypads.source.git.commit", repo.head.object.hexsha)

        except Exception as e:
            logger.warning("Checking the index of your repository failed due to %s" % str(e))


def check_existing_branches(repo, ref='HEAD'):
    # get the branches created by PyPads
    branches = {b.name: b for b in repo.branches if "PyPads" in b.name}

    # get the tags saved by PyPads
    tags = [t.tag for t in repo.tags if 'PyPads' in t.path]
    try:
        for tag in tags:
            diff = repo.git.diff(ref, tag.tag, '--raw')
            if diff == tag.message:
                print("found a branch with the same changes")
                return branches.get(tag.tag), repo.git.diff(ref, tag.tag)
    except Exception as e:
        logger.info("Checking existing branches failed due to %s" % str(e))
        return None, None
    return None, None


def add_files(repo):
    untracked_files = repo.untracked_files
    if untracked_files and len(untracked_files) > 0:
        repo.index.add(untracked_files)
    if len([item.a_path for item in repo.index.diff(None)]) > 0:
        repo.git.add(A=True)


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
