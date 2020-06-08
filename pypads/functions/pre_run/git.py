from pypads.functions.pre_run.pre_run import PreRunFunction
from pypads.managed_git import ManagedGit


class IGit(PreRunFunction):

    @staticmethod
    def _needed_packages():
        return ['git']

    def _call(self, pads, *args, **kwargs):
        _pypads_timeout = kwargs.get("_pypads_timeout") if kwargs.get("_pypads_timeout") else 5
        run = pads.api.active_run()
        tags = run.data.tags
        source_name = tags.get("mlflow.source.name", None)
        managed_git: ManagedGit = pads.managed_git_factory(source_name)
        import ipdb
        ipdb.set_trace()
        if managed_git:
            repo = managed_git.repo

            # Disable pager for returns
            repo.git.set_persistent_git_options(no_pager=True)
            pads.api.set_tag("pypads.git.description", repo.description)
            pads.api.set_tag("pypads.git.describe", repo.git.describe("--all"))
            from git import GitCommandError
            # try:
            #     pads.api.set_tag("pypads.git.shortlog", repo.git.shortlog(kill_after_timeout=_pypads_timeout))
            # except GitCommandError as e:
            #     warning("Ignored the execution and tracking of 'git shortlog'. " + str(e))
            try:
                pads.api.log_mem_artifact("pypads.git.log", repo.git.log(kill_after_timeout=_pypads_timeout))
            except GitCommandError as e:
                pass
            remotes = repo.remotes
            remote_out = "No remotes existing"
            if len(remotes) > 0:
                remote_out = ""
                for remote in remotes:
                    remote_out += remote.name + ": " + remote.url + "\n"
            pads.api.set_tag("pypads.git.remotes", remote_out)
