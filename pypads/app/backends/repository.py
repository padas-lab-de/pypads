import os
from contextlib import contextmanager
from typing import Union
from uuid import uuid4

from pydantic import Extra

from pypads.app.backends.mlflow import MongoSupportMixin
from pypads.model.models import EntryModel, to_reference, BaseStorageModel, IdReference, \
    get_reference, ExperimentModel, RunModel
from pypads.utils.logging_util import FileFormats


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
            self.pads.backend.set_experiment_tag(repo.experiment_id, Repository.__class__.__name__, True)
        self._repo = repo
        self._object_cache = {}

    @staticmethod
    def is_repository(experiment):
        return Repository.__class__.__name__ in experiment.tags

    def get_object(self, run_id=None, uid=None, name=None):
        """
        Gets a persistent object to store to. This is a mapping to a run and not the object itself.
        :param name: Set a name for the object.
        :param uid: Optional uid of object. This allows only for one run storing the object with uid.
        :param run_id: Optional run_id of object. This is the id of the run in which the object should be stored.
        :return:
        """
        if uid not in self._object_cache:
            repo_obj = RepositoryObject(self, run_id, uid, name)
            self._object_cache[uid] = repo_obj
            return repo_obj
        else:
            return self._object_cache[uid]

    def has_object(self, uid):
        if uid in self._object_cache:
            return True
        if isinstance(self.pads.backend, MongoSupportMixin):
            return self.pads.backend.get_json(self.repo_reference(uid)) is not None
        else:
            return len(self.pads.backend.search_runs(experiment_ids=self.id,
                                                     filter_string="tags.`pypads_unique_uid` = \"" +
                                                                   self.repo_reference(uid).id + "\"")) > 0

    def repo_reference(self, uid, run_id=-1):
        """
        Translates a uid in a uid hash with the repos meta information.
        :param run_id:
        :param uid:
        :return:
        """
        return to_reference({
            "uid": uid,
            "storage_type": self.name,
            "experiment": get_reference(ExperimentModel(uid=self.id, name=self.name)),
            "backend_uri": self.pads.backend.uri,
            "run": get_reference(RunModel(uid=str(run_id))),
            # The run_id is here not important the run doesn't exist right now
            "category": self.name
        })

    def context(self, run_id=None, run_name=None):
        """
        Activates the repository context by setting an intermediate run.
        :param run_name: A name for the run. This will also be chosen automatically if None.
        :param run_id: Id of the run to log into. If none is given a new one is created
        :return:
        """

        if run_id:
            if self.pads.api.active_run() and run_id == self.pads.api.active_run().info.run_id:
                @contextmanager
                def active_reference():
                    yield self.pads.api.active_run()

                return active_reference()
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

    def __init__(self, repository, run_id, uid, name=None):
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
        self._uid = uid if uid is not None else uuid4()
        self._run_id = run_id

    def get_reference(self):
        """
        Function to build a reference to the repository object. (And it's internal singular json)
        :return:
        """
        reference = self.repository.repo_reference(self.uid)
        reference.run = get_reference(RunModel(uid=str(self.run_id)))
        return reference

    @property
    def uid(self):
        return self._uid

    @property
    def repo_reference(self):
        return self.repository.repo_reference(uid=self.uid)

    def init_run_storage(self):
        # if self._run is None:
        # UID is given. Check for existence.
        if self._run is None:
            runs = self.pads.backend.search_runs(experiment_ids=self.repository.id,
                                                 filter_string="tags.`pypads_unique_uid` = \"" + self.repo_reference.id
                                                               + "\"")

            # If exists set the run_id to the existing one instead
            if len(runs) > 0:
                # TODO is this correct? Mlflow returns a dataframe
                self._run = self.pads.results.get_run(run_id=runs.iloc[0][0])

            # If no run_id was found with uid create a new run and get its id
            if self._run is None:
                if self._run_id is None:
                    # If a uid is given and the tag for the run is not set already set it
                    self._run = self.pads.backend \
                        .create_run(experiment_id=self.repository.id,
                                    tags={"pypads_unique_uid": self.repo_reference.id})
                    self._run_id = self._run.info.run_id
                else:
                    self._run = self.pads.results.get_run(run_id=self._run_id)

    def init_context(self):
        return self.repository.context(self.run_id, run_name=self._name)

    @property
    def run(self):
        self.init_run_storage()
        return self._run

    @property
    def run_id(self):
        return self.run.info.run_id

    def log_mem_artifact(self, path, obj, write_format=FileFormats.text, description="", additional_data=None,
                         holder=None):
        """
        Activates the repository context and stores an artifact from memory into it.
        :return:
        """
        with self.init_context() as ctx:
            return self.get_rel_artifact_path(
                self.pads.api.log_mem_artifact(path=path, obj=obj, write_format=write_format, description=description,
                                               additional_data=self._extend_meta(additional_data), holder=holder))

    def log_artifact(self, local_path, description="", additional_data=None, artifact_path=None, holder=None):
        """
        Activates the repository context and stores an artifact into it.
        :return:
        """
        with self.init_context():
            return self.get_rel_artifact_path(
                self.pads.api.log_artifact(local_path=local_path, description=description,
                                           additional_data=self._extend_meta(additional_data),
                                           artifact_path=artifact_path, holder=holder))

    def log_param(self, key, value, value_format=None, description="", meta: dict = None, holder=None):
        """
        Activates the repository context and stores an parameter into it.
        :return:
        """
        with self.init_context() as ctx:
            return self.get_rel_artifact_path(
                self.pads.api.log_param(key, value, value_format, description, self._extend_meta(meta), holder=holder))

    def log_metric(self, key, value, description="", step=None, meta: dict = None, holder=None):
        """
        Activates the repository context and stores an metric into it.
        :return:
        """
        with self.init_context() as ctx:
            return self.get_rel_artifact_path(
                self.pads.api.log_metric(self, key, value, description, step, self._extend_meta(meta), holder=holder))

    def set_tag(self, key, value, value_format="string", description="", meta: dict = None, holder=None):
        """
        Activates the repository context and stores an tag into it.
        :return:
        """
        if isinstance(self.pads.backend, MongoSupportMixin):
            return self.pads.api.set_tag(key, value, value_format, description, meta)
        else:
            with self.init_context() as ctx:
                return self.get_rel_artifact_path(
                    self.pads.api.set_tag(key, value, value_format, description, self._extend_meta(meta),
                                          holder=holder))

    def reference_dict(self):
        """
        Dict of the repo object to extend the passed json on.
        :return:
        """
        return {
            "uid": self.uid,
            "repository": self.repo_reference,
            "storage_type": self.repository.name,
            "experiment": get_reference(ExperimentModel(uid=self.repository.id, name=self.repository.name)),
            "backend_uri": self.pads.backend.uri,
            "run": get_reference(RunModel(uid=str(self.run_id))),
            # The run_id is here not important the run doesn't exist right now
            "category": self.repository.name
        }

    def log_json(self, obj: Union[EntryModel, dict]):
        """
        Logs a single given object as the json object representing the repository object.
        :param obj: Object to store as json. storage_type gets set to the respective repository name value
        :return:
        """
        if isinstance(obj, dict):
            obj = RepositoryEntryModel(**self._extend_meta({**obj, **self.reference_dict()}))
        else:
            if hasattr(obj, "experiment"):
                obj.experiment = get_reference(ExperimentModel(uid=self.repository.id, name=self.repository.name))
            if hasattr(obj, "run"):
                obj.run = get_reference(RunModel(uid=str(self.run_id)))
            obj = RepositoryEntryModel(**self._extend_meta({**obj.dict(by_alias=True), **self.reference_dict()}))
        if isinstance(self.pads.backend, MongoSupportMixin):
            return self.pads.backend.log_json(obj)
        else:
            with self.init_context() as ctx:
                return self.pads.backend.log(obj)

    def get_json(self):
        """
        Get the representing json object.
        :return:
        """
        if isinstance(self.pads.backend, MongoSupportMixin):
            return self.pads.backend.get_json(to_reference(self.reference_dict()))
        else:
            with self.init_context() as ctx:
                return self.pads.backend.get_json(to_reference(self.reference_dict()))

    def _extend_meta(self, meta=None):

        if meta is None:
            meta = {}

        return {**meta, "backend_uri": self.pads.uri}

    def get_rel_base_path(self):
        return os.path.join(self.repository.id, self.run_id)

    def get_rel_artifact_path(self, path):
        if isinstance(self.pads.backend, MongoSupportMixin):
            return path.id
        return os.path.join(self.get_rel_base_path(), "artifacts", str(path))


class RepositoryEntryModel(BaseStorageModel):
    repository: IdReference = ...

    class Config:
        extra = Extra.allow


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


class LibraryRepository(Repository):

    def __init__(self, *args, **kwargs):
        """
        Repository holding all the relevant tracked library information
        :param args:
        :param kwargs:
        """
        super().__init__(*args, name="pypads_libraries", **kwargs)


class MappingRepository(Repository):

    def __init__(self, *args, **kwargs):
        """
        Repository holding all the relevant mapping information
        :param args:
        :param kwargs:
        """
        super().__init__(*args, name="pypads_mappings", **kwargs)
