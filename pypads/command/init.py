import os

from git import Repo


def init():
    """
    Function to initialize the pypads managed repo
    :return:
    """
    cwd = os.getcwd()
    if not os.path.exists(cwd + "/.git"):
        raise EnvironmentError("A git repository has to be defined for pypads to work.")

    if os.path.exists(cwd + "/.pypads"):
        raise EnvironmentError("Pypads is already initialized.")

    os.makedirs(cwd + "/.pypads")

    with open(".gitignore", "w+") as file:
        file.write("*")

    git_repo = Repo(os.getcwd())

