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


def get_git_repo(path):
    if _is_package_available("git"):
        import git
        if os.path.isfile(path):
            path = os.path.dirname(path)
        return git.Repo(path, search_parent_directories=True)
    else:
        warning("Git needs to be installed to manage a central repository.")
        return None


class RemoteProvider:
    __metaclass__ = ABCMeta

    @abstractmethod
    def mirror(self):
        pass


class GitLabRemoteProvider(RemoteProvider):
    pass
