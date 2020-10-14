import os
from typing import Union, Optional
from uuid import uuid4

from pydantic import BaseModel, Extra

from pypads.app.backends.mlflow import MongoSupportMixin
from pypads.model.models import Entry, join_typed_id, IdBasedEntry
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

    @staticmethod
    def is_repository(experiment):
        return Repository.__class__.__name__ in experiment.tags

    def get_object(self, run_id=None, uid=None, name=None):
        """
        Gets a persistent object to store to.
        :param name: Set a name for the object.
        :param uid: Optional uid of object. This allows only for one run storing the object with uid.
        :param run_id: Optional run_id of object. This is the id of the run in which the object should be stored.
        :return:
        """
        return RepositoryObject(self, run_id, uid, name)

    def has_object(self, uid):
        if isinstance(self.pads.backend, MongoSupportMixin):
            return self.pads.backend.get_json(self.id, uid, self.name) is not None
        else:
            return len(self.pads.backend.search_runs(experiment_ids=self.id,
                                                     filter_string="tags.`pypads_unique_uid` = \"" + join_typed_id(
                                                         [uid, self.name]) + "\"")) > 0

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
        self._uid = uid
        self._run_id = run_id

    @property
    def uid(self):
        return self._uid

    @property
    def joined_uid(self):
        return join_typed_id([self.uid, self.repository.name])

    def _init_run_storage(self):
        # if self._run is None:
        # UID is given. Check for existence.
        if self.uid:
            runs = self.pads.backend.search_runs(experiment_ids=self.repository.id,
                                                 filter_string="tags.`pypads_unique_uid` = \"" + self.joined_uid
                                                               + "\"")

            # If exists set the run_id to the existing one instead
            if len(runs) > 0:
                # TODO is this correct? Mlflow returns a dataframe
                self._run = self.pads.api.get_run(run_id=runs.iloc[0][0])

        # If no run_id was found with uid create a new run and get its id
        if self.run is None:
            if self._run_id is None:
                # If a uid is given and the tag for the run is not set already set it
                self._run = self.pads.backend \
                    .create_run(experiment_id=self.repository.id,
                                tags={"pypads_unique_uid": str(
                                    self.joined_uid)} if self.uid else None)
                self._run_id = self._run.info.run_id
            else:
                self._run = self.pads.api.get_run(run_id=self._run_id)

    def init_context(self):
        self._init_run_storage()
        return self.repository.context(self.run_id, run_name=self._name)

    @property
    def run(self):
        return self._run

    @property
    def run_id(self):
        return self.run.info.run_id

    def log_mem_artifact(self, path, obj, write_format=FileFormats.text, description="", additional_data=None):
        """
        Activates the repository context and stores an artifact from memory into it.
        :return:
        """
        with self.init_context() as ctx:
            return self.get_rel_artifact_path(
                self.pads.api.log_mem_artifact(path=path, obj=obj, write_format=write_format, description=description,
                                               additional_data=additional_data))

    def log_artifact(self, local_path, description="", additional_data=None, artifact_path=None):
        """
        Activates the repository context and stores an artifact into it.
        :return:
        """
        with self.init_context() as ctx:
            return self.get_rel_artifact_path(
                self.pads.api.log_artifact(local_path=local_path, description=description,
                                           additional_data=additional_data,
                                           artifact_path=artifact_path))

    def log_param(self, key, value, value_format=None, description="", meta: dict = None):
        """
        Activates the repository context and stores an parameter into it.
        :return:
        """
        with self.init_context() as ctx:
            return self.get_rel_artifact_path(self.pads.api.log_param(key, value, value_format, description, meta))

    def log_metric(self, key, value, description="", step=None, meta: dict = None):
        """
        Activates the repository context and stores an metric into it.
        :return:
        """
        with self.init_context() as ctx:
            return self.get_rel_artifact_path(self.pads.api.log_metric(self, key, value, description, step, meta))

    def set_tag(self, key, value, value_format="string", description="", meta: dict = None):
        """
        Activates the repository context and stores an tag into it.
        :return:
        """
        if isinstance(self.pads.backend, MongoSupportMixin):
            return self.pads.api.set_tag(key, value, value_format, description, meta)
        else:
            with self.init_context() as ctx:
                return self.get_rel_artifact_path(self.pads.api.set_tag(key, value, value_format, description, meta))

    def log_json(self, obj: Union[Entry, dict]):
        """
        Logs a single given object as the json object representing the repository object.
        :param obj: Object to store as json. storage_type gets set to the respective repository name value
        :return:
        """
        with self.init_context() as ctx:
            if isinstance(obj, dict):
                obj = ExtendedIdBasedEntry(**{**obj,
                                              **{"uid": str(self.uid), "storage_type": self.repository.name,
                                                 "run_id": self.run_id, "experiment_id": self.repository.id}})
            else:
                obj = ExtendedIdBasedEntry(
                    **{**obj.dict(by_alias=True),
                       **{"uid": str(self.uid), "storage_type": self.repository.name, "run_id": self.run_id,
                          "experiment_id": self.repository.id}})
            # if isinstance(self.pads.backend, MongoSupportMixin):
            #     return self.pads.backend.log(obj)
            # else:
            #     with self.init_context() as ctx:
            return self.pads.backend.log(obj)

    def get_json(self):
        """
        Get the representing json object.
        :return:
        """
        if isinstance(self.pads.backend, MongoSupportMixin):
            if self.uid is None:
                self._uid = uuid4()
            return self.pads.backend.get_json(self.repository.id, self.uid, self.repository.name)
        else:
            with self.init_context() as ctx:
                return self.pads.backend.get_json(self.run_id, self.uid, self.repository.name)

    def get_rel_base_path(self):
        return os.path.join(self.repository.id, self.run_id)

    def get_rel_artifact_path(self, path):
        return os.path.join(self.get_rel_base_path(), "artifacts", path)


class ExtendedIdBasedEntry(IdBasedEntry):
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


class BaseRepositoryObjectModel(BaseModel):
    """
    Extend this class if you want to store json directly into a repository
    """
    storage_type: Optional[str] = None
    run_id: Optional[str] = None
