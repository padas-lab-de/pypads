import os

repository_experiments = []


class Repository:

    def __init__(self, *args, name, **kwargs):
        """
        This class abuses mlflow experiments as arbitrary stores.
        :param args:
        :param name: Name of the repository experiment.
        :param kwargs:
        """
        # get the repo or create new where datasets are stored
        self._name = name
        from pypads.app.pypads import get_current_pads
        self.pads = get_current_pads()
        repo = self.pads.backend.get_experiment_by_name(name)

        if repo is None:
            repo = self.pads.backend.get_experiment(self.pads.backend.create_experiment(name))
        self._repo = repo

        repository_experiments.append(repo.experiment_id)

    def get_object(self, run_id=None, uid=None, name=None):
        """
        Gets a persistent object to store to.
        :param name: Set a name for the object.
        :param uid: Optional uid of object. This allows only for one run storing the object with uid.
        :param run_id: Optional run_id of object. This is the id of the run in which the object should be stored.
        :return:
        """
        return RepositoryObject(self, run_id, uid, name)

    def has_object(self, uid=None):
        return len(self.pads.backend.search_runs(experiment_ids=self.id,
                                                 filter_string="tags.`pypads_unique_uid` = \"" + str(uid) + "\""))

    def context(self, run_id=None, run_name=None):
        """
        Activates the repository context by setting an intermediate run.
        :param run_name: A name for the run. This will also be chosen automatically if None.
        :param run_id: Id of the run to log into. If none is given a new one is created
        :return:
        """

        if run_id:
            return self.pads.api.intermediate_run(experiment_id=self.id, run_id=run_id, run_name=run_name,
                                                  setups=False)
        else:
            return self.pads.api.intermediate_run(experiment_id=self.id, run_name=run_name,
                                                  setups=False)

    @property
    def name(self):
        return self._name

    @property
    def repo(self):
        return self._repo

    @property
    def id(self):
        return self._repo.experiment_id


class RepositoryObject:

    def __init__(self, repository, run_id, uid, name):
        """
        This is a representation of an object in the repository. It is stored as a run into mlflow. It can be identified
        by either a run_id or by a uid.
        :param repository:
        :param run_id:
        :param uid:
        :param name: Name for the object
        """
        self.repository = repository
        from pypads.app.pypads import get_current_pads
        self.pads = get_current_pads()
        self._name = name

        self.run_id = run_id
        if uid:
            runs = self.pads.backend.search_runs(experiment_ids=self.repository.id,
                                                 filter_string="tags.`pypads_unique_uid` = \"" + str(uid) + "\"")
            if len(runs) > 0:
                self.run_id = runs.pop().info.run_id

        if self.run_id is None:
            self.run_id = self.pads.backend.create_run(experiment_id=self.repository.id).info.run_id

        if uid:
            self.set_tag("pypads_unique_uid", uid,
                         "Unique id of the object. This might be a hash for a dataset or similar.")

    def log_mem_artifact(self, *args, **kwargs):
        """
        Activates the repository context and stores an artifact from memory into it.
        :param args:
        :param run_id: Id of the run to log into. If none is given a new one is created
        :param kwargs:
        :return:
        """
        with self.repository.context(self.run_id, run_name=self._name) as ctx:
            return self.pads.api.log_mem_artifact(*args, **kwargs)

    def log_artifact(self, *args, **kwargs):
        """
        Activates the repository context and stores an artifact into it.
        :param args:
        :param run_id: Id of the run to log into. If none is given a new one is created
        :param kwargs:
        :return:
        """
        with self.repository.context(self.run_id, run_name=self._name) as ctx:
            return self.pads.api.log_artifact(*args, **kwargs)

    def log_param(self, *args, **kwargs):
        """
        Activates the repository context and stores an parameter into it.
        :param args:
        :param run_id: Id of the run to log into. If none is given a new one is created
        :param kwargs:
        :return:
        """
        with self.repository.context(self.run_id, run_name=self._name) as ctx:
            self.pads.api.log_param(*args, **kwargs)

    def log_metric(self, *args, **kwargs):
        """
        Activates the repository context and stores an metric into it.
        :param args:
        :param run_id: Id of the run to log into. If none is given a new one is created
        :param kwargs:
        :return:
        """
        with self.repository.context(self.run_id, run_name=self._name) as ctx:
            self.pads.api.log_metric(*args, **kwargs)

    def set_tag(self, *args, **kwargs):
        """
        Activates the repository context and stores an tag into it.
        :param args:
        :param run_id: Id of the run to log into. If none is given a new one is created
        :param kwargs:
        :return:
        """
        with self.repository.context(self.run_id, run_name=self._name) as ctx:
            self.pads.api.set_tag(*args, **kwargs)

    def get_rel_base_path(self):
        return os.path.join(self.repository.id, self.run_id)

    def get_artifact_path(self, path):
        return os.path.join(self.get_rel_base_path(), "artifacts", path)


class SchemaRepository(Repository):

    def __init__(self, *args, **kwargs):
        """
        Repository holding all the relevant schema information
        :param args:
        :param kwargs:
        """
        super().__init__(*args, name="pypads_schemata", **kwargs)
