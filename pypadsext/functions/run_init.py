from pypadsext.code.storage import get_run_git, get_git_repo


def git_meta(pads):
    run = pads.api.active_run()
    tags = run.data.tags
    source_name = tags.get("mlflow.source.name", None)
    repo = get_git_repo(source_name) if source_name else None
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


def git_mirror(pads):
    if pads.config["mirror_git"]:
        repo = get_run_git()
        if repo:
            # TODO mirror the given repo to our git remote server
            pass
