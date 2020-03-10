import os
from abc import ABCMeta, abstractmethod
from logging import warning

from pypadsext.util import _is_package_available


def get_run_git():
    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()
    run = pads.api.active_run()
    tags = run.data.tags
    source_name = tags.get("mlflow.source.name", None)
    if source_name:
        return get_git_repo(source_name)
    return None


def get_git_repo(path, pads=None):
    if _is_package_available("git"):
        import git
        if os.path.isfile(path):
            path = os.path.dirname(path)
            from git import InvalidGitRepositoryError
            try:
                repo = git.Repo(path, search_parent_directories=True)
                check_index(repo, message="PyPadrePads issued commit", pads=pads)
                return repo
            except InvalidGitRepositoryError:
                return init_git_repo(path, pads=pads)
    else:
        warning("Git needs to be installed to manage a central repository.")
        return None


def init_git_repo(path, pads=None):
    if _is_package_available("git"):
        import git
        from git import InvalidGitRepositoryError, GitCommandError, GitError
        try:
            repo = git.Repo.init(path, bare=False)
            check_index(repo, message="PyPadrePads initialized repository.", init=True, pads=pads)
            return repo
        except (InvalidGitRepositoryError, GitCommandError, GitError):
            warning("Git could not initialize a repository in this directory %s" % path)
            return None
    else:
        warning("Git needs to be installed to manage a central repository.")
        return None


def check_index(repo, message="", init=False, pads=None):
    if not pads:
        from pypads.base import get_current_pads
        from pypadsext.base import PyPadrePads
        pads: PyPadrePads = get_current_pads()
    run = pads.api.active_run()
    if init:
        add_files(repo)
        repo.git.commit(message=message)
        pads.api.set_tag("pypads.source.git.commit", repo.head.object.hexsha)
        pads.api.set_tag("pypads.git.branch", repo.active_branch.name)
    else:
        curr_branch = repo.active_branch.name
        if len(repo.index.diff('HEAD')) > 0 or len(repo.index.diff(None)) > 0 or repo.untracked_files:
            warning(
                "There are uncommitted changes, stashing, branching out, committing, reverting back and unstashing...")
            
            # Save those changes to stash
            repo.git.stash('push')

            # branch out, apply the stashed changes and commit
            new_branch = "PyPads/{}".format(run.info.run_id)
            repo.git.checkout(curr_branch, b=new_branch)
            pads.api.set_tag("pypads.git.branch", new_branch)
            repo.git.stash('apply')
            add_files(repo)
            repo.git.commit(message=message)

            pads.api.set_tag("pypads.source.git.commit", repo.head.object.hexsha)
            # checkout to the master branch and pop the stash
            repo.git.checkout(curr_branch)
            repo.git.stash('pop')
        else:
            pads.api.set_tag("pypads.git.branch", curr_branch)
            pads.api.set_tag("pypads.source.git.commit", repo.head.object.hexsha)


def add_files(repo):
    untracked_files = repo.untracked_files
    if untracked_files and len(untracked_files) > 0:
        repo.index.add(untracked_files)
    if len([item.a_path for item in repo.index.diff(None)]) > 0:
        repo.git.add(A=True)


class RemoteProvider:
    __metaclass__ = ABCMeta

    @abstractmethod
    def mirror(self):
        pass


class GitLabRemoteProvider(RemoteProvider):
    pass
