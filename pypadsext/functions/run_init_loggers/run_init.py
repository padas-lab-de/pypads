from pypads.functions.run_init_loggers.base_run_init_logger import RunInitLoggingFunction

from pypadsext.code.storage import get_run_git, get_git_repo


class GitMeta(RunInitLoggingFunction):

    @staticmethod
    def _needed_packages():
        return ['git']

    def _call(self, pads, *args, **kwargs):
        run = pads.api.active_run()
        tags = run.data.tags
        source_name = tags.get("mlflow.source.name", None)
        repo = get_git_repo(source_name, pads=pads) if source_name else None
        if repo:
            # Disable pager for returns
            repo.git.set_persistent_git_options(no_pager=True)
            pads.api.set_tag("pypads.git.description", repo.description)
            pads.api.set_tag("pypads.git.describe", repo.git.describe("--all"))
            from git import GitCommandError
            try:
                pads.api.set_tag("pypads.git.shortlog", repo.git.shortlog(kill_after_timeout=5))
            except GitCommandError:
                pass
            try:
                pads.api.set_tag("pypads.git.log", repo.git.log(kill_after_timeout=5))
            except GitCommandError:
                pass
            remotes = repo.remotes
            remote_out = "No remotes existing"
            if len(remotes) > 0:
                remote_out = ""
                for remote in remotes:
                    remote_out += remote.name + ": " + remote.url + "\n"
            pads.api.set_tag("pypads.git.remotes", remote_out)


class GitMirror(RunInitLoggingFunction):

    @staticmethod
    def _needed_packages():
        return ['git']

    def _call(self, pads, *args, **kwargs):
        if pads.config["mirror_git"]:
            repo = get_run_git()
            if repo:
                # TODO mirror the given repo to our git remote server
                pass

# TODO find a good usage
# def source_code_parsing(pads):
#     pads.api.register_post_fn("tag_extraction", tag_extraction)
#     run = pads.api.active_run()
#     tags = run.data.tags
#     source_name = tags.get("mlflow.source.name", None)
#     code = None
#     if source_name:
#         with open(source_name) as f:
#             code = f.read()
#     else:
#         import sys
#         source = sys.argv[0]
#         if "unittest" not in source.split('.')[-2]:
#             with open(source) as f:
#                 code = f.read()
#         else:
#             warning("The source code is being run from a unit test")
#     if code:
#         pads.cache.add("source_code", code)
