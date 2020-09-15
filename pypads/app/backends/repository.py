from pypads.app.pypads import get_current_pads


class Repository:

    def __init__(self, *args, name, **kwargs):
        """
            This class abuses mlflow experiments as arbitrary stores.
        :param args:
        :param name: Name of the repository experiment.
        :param kwargs:
        """
        # get the repo or create new where datasets are stored
        self.name = name
        self.pads = get_current_pads()
        repo = self.pads.mlf.get_experiment_by_name(name)

        if repo is None:
            repo = self.pads.mlf.get_experiment(self.pads.mlf.create_experiment(name))
        self.repo = repo

    def log_mem_artifact(self, *args, run_id=None, **kwargs):
        """
        Activates the repository context and stores an artifact from memory into it.
        :param args:
        :param run_id: Id of the run to log into. If none is given a new one is created
        :param kwargs:
        :return:
        """
        with self.repository_context(run_id=run_id) as ctx:
            self.pads.api.log_mem_artifact(*args, **kwargs)

    def log_artifact(self, *args, run_id=None, **kwargs):
        """
        Activates the repository context and stores an artifact into it.
        :param args:
        :param run_id: Id of the run to log into. If none is given a new one is created
        :param kwargs:
        :return:
        """
        with self.repository_context(run_id=run_id) as ctx:
            self.pads.api.log_artifact(*args, **kwargs)

    def log_param(self, *args, run_id=None, **kwargs):
        """
        Activates the repository context and stores an parameter into it.
        :param args:
        :param run_id: Id of the run to log into. If none is given a new one is created
        :param kwargs:
        :return:
        """
        with self.repository_context(run_id=run_id) as ctx:
            self.pads.api.log_param(*args, **kwargs)

    def log_metric(self, *args, run_id=None, **kwargs):
        """
        Activates the repository context and stores an metric into it.
        :param args:
        :param run_id: Id of the run to log into. If none is given a new one is created
        :param kwargs:
        :return:
        """
        with self.repository_context(run_id=run_id) as ctx:
            self.pads.api.log_metric(*args, **kwargs)

    def set_tag(self, *args, run_id=None, **kwargs):
        """
        Activates the repository context and stores an tag into it.
        :param args:
        :param run_id: Id of the run to log into. If none is given a new one is created
        :param kwargs:
        :return:
        """
        with self.repository_context(run_id=run_id) as ctx:
            self.pads.api.set_tag(*args, **kwargs)

    def repository_context(self, run_id=None):
        """
        Activates the repository context by setting an intermediate run.
        :param run_id: Id of the run to log into. If none is given a new one is created
        :return:
        """
        # TODO what happens if already exists?
        if run_id:
            return self.pads.api.intermediate_run(experiment_id=self.name, run_id=run_id)
        else:
            return self.pads.api.intermediate_run(experiment_id=self.name)
