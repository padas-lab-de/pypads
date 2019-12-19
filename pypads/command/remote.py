def remote():
    """
    Function to run an arbitrary command in the git repository.
    :return:
    """
    import subprocess
    process = subprocess.Popen(['ls', '-l'], stdout=subprocess.PIPE)
    for line in process.stdout:
        print(line.decode().strip())
