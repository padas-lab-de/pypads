import os
from abc import ABCMeta, abstractmethod
from logging import warning, info

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
                warning("No existing git repository was found, initializing a new one...")
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
            info("Repository was successfully initialized")
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
        try:
            add_files(repo)
            repo.git.commit(message=message)
            pads.api.set_tag("pypads.source.git.commit", repo.head.object.hexsha)
            pads.api.set_tag("pypads.git.branch", repo.active_branch.name)

        except Exception as e:
            warning("Could not issue the first commit due to this error %s" % str(e))
    else:
        try:
            orig_branch = repo.active_branch.name
            if len(repo.index.diff('HEAD')) > 0 or len(repo.index.diff(None)) > 0 or repo.untracked_files:
                warning("There are uncommitted changes, stashing, branching out, "
                        "committing, reverting back and unstashing...")
                # Save those changes to stash
                repo.git.stash('push', '--include-untracked')

                # check if the changes were already tracked by PyPads
                branch, diff = check_existing_branches(repo, ref=orig_branch)

                if not branch:
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
            warning("Checking the index of your repository failed due to %s" % str(e))


def check_existing_branches(repo, ref='HEAD'):
    # get the branches created by PyPads
    branches = {b.name: b for b in repo.branches if "PyPads" in b.name}

    # get the tags saved by PyPads
    tags = [t.tag for t in repo.tags if 'PyPads' in t.path]
    try:
        for tag in tags:
            diff = repo.git.diff(ref, tag.tag, '--raw')
            if diff == tag.message:
                return branches.get(tag.tag), repo.git.diff(ref, tag.tag)
    except Exception as e:
        info("Checking existing branches failed due to %s" % str(e))
        return None, None
    return None, None


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
