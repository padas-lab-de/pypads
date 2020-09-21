import os

from pypads.utils.logging_util import FileFormats

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
        self._run = None

        # UID is given. Check for existence.
        if uid:
            runs = self.pads.backend.search_runs(experiment_ids=self.repository.id,
                                                 filter_string="tags.`pypads_unique_uid` = \"" + str(uid) + "\"")

            # If exists set the run_id to the existing one instead
            if len(runs) > 0:
                # TODO is this correct? Mlflow returns a dataframe
                self._run = self.pads.api.get_run(run_id=runs.iloc[0][0])

        # If no run_id was found with uid create a new run and get its id
        if self.run is None:
            if run_id is None:
                # If a uid is given and the tag for the run is not set already set it
                self._run = self.pads.backend.create_run(experiment_id=self.repository.id,
                                                         tags={"pypads_unique_uid": uid} if uid else None)
            else:
                self._run = self.pads.api.get_run(run_id=run_id)

    @property
    def run(self):
        return self._run

    @property
    def run_id(self):
        return self.run.info.run_id

    def log_mem_artifact(self, path, obj, write_format=FileFormats.text, description="", meta=None, write_meta=True):
        """
        Activates the repository context and stores an artifact from memory into it.
        :return:
        """
        with self.repository.context(self.run_id, run_name=self._name) as ctx:
            return self.get_rel_artifact_path(
                self.pads.api.log_mem_artifact(path, obj, write_format, description=description, meta=meta,write_meta=write_meta))

    def log_artifact(self, local_path, description="", meta=None, artifact_path=None):
        """
        Activates the repository context and stores an artifact into it.
        :return:
        """
        with self.repository.context(self.run_id, run_name=self._name) as ctx:
            return self.get_rel_artifact_path(
                self.pads.api.log_artifact(local_path, description, meta, artifact_path))

    def log_param(self, key, value, value_format=None, description="", meta: dict = None):
        """
        Activates the repository context and stores an parameter into it.
        :return:
        """
        with self.repository.context(self.run_id, run_name=self._name) as ctx:
            return self.get_rel_artifact_path(self.pads.api.log_param(key, value, value_format, description, meta))

    def log_metric(self, key, value, description="", step=None, meta: dict = None):
        """
        Activates the repository context and stores an metric into it.
        :return:
        """
        with self.repository.context(self.run_id, run_name=self._name) as ctx:
            return self.get_rel_artifact_path(self.pads.api.log_metric(self, key, value, description, step, meta))

    def set_tag(self, key, value, value_format="string", description="", meta: dict = None):
        """
        Activates the repository context and stores an tag into it.
        :return:
        """
        with self.repository.context(self.run_id, run_name=self._name) as ctx:
            return self.get_rel_artifact_path(self.pads.api.set_tag(key, value, value_format, description, meta))

    def get_rel_base_path(self):
        return os.path.join(self.repository.id, self.run_id)

    def get_rel_artifact_path(self, path):
        return os.path.join(self.get_rel_base_path(), "artifacts", path)


class SchemaRepository(Repository):

    def __init__(self, *args, **kwargs):
        """
        Repository holding all the relevant schema information
        :param args:
        :param kwargs:
        """
        super().__init__(*args, name="pypads_schemata", **kwargs)


class LoggerRepository(Repository):

    def __init__(self, *args, **kwargs):
        """
        Repository holding all the relevant logger information
        :param args:
        :param kwargs:
        """
        super().__init__(*args, name="pypads_logger", **kwargs)
