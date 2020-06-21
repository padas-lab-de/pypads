import uuid
from abc import ABCMeta, abstractmethod

from pypads.app.misc.mixins import SuperStop
from pypads.injections.analysis.call_tracker import LoggingEnv


# noinspection PyUnusedLocal,PyShadowingNames,PyProtectedMember
class ValidateableMixin(SuperStop):
    __metaclass__ = ABCMeta
    """ This class implements basic logic for validating the tracked object"""

    # noinspection PyBroadException
    def __init__(self, *args, metadata, **kwargs):
        super().__init__(*args, **kwargs)

        self.validate(metadata=metadata, **kwargs)

    @abstractmethod
    def validate(self, **kwargs):
        raise NotImplementedError()



class MetadataMixin(ValidateableMixin):
    __metaclass__ = ABCMeta
    """
    Base object for tracked objects that manage metadata. A MetadataEntity manages and id and a dict of metadata.
    The metadata should contain all necessary non-binary data to describe an entity.
    """

    METADATA = "metadata"
    CREATED_AT = 'created_at'
    LAST_MODIFIED_BY = 'last_modified_by'
    COMPUTED_BY = 'computed_by'
    EXECUTION_TIME = 'execution_time'
    TRACKED_BY = 'tracked_by'
    LOGGING_TIME = 'logging_time'


    @abstractmethod
    def __init__(self, *, _pypads_env:LoggingEnv, metadata: dict, **kwargs):

        import time
        #Todo add metadata
        self._metadata = {**{"id": uuid.uuid4().__str__(), self.CREATED_AT: time.time()},
                    **metadata}

        super().__init__(**{"metadata": metadata, **kwargs})


    @property
    def id(self):
        """
        returns the unique id of the data set. Data sets will be managed on the basis of this id
        :return: string
        """
        return self.metadata["id"]

    @id.setter
    def id(self, _id):
        """
        used for updating the id after the undlerying generic has assigned one
        :param _id: id, ideally an url
        :return:
        """
        self.metadata["id"] = _id

    @property
    def name(self):
        """
        returns the name of this object, which is expected in field "name" of the metadata. If this field does not
        exist, the id is returned
        :return:
        """
        if self.metadata and "name" in self.metadata:
            return self.metadata["name"]
        else:
            return str(self.id)

    @name.setter
    def name(self, name):
        self.metadata["name"] = name

    @property
    def created_at(self):
        if self.CREATED_AT in self.metadata:
            return self.metadata[self.CREATED_AT]
        else:
            return None

    @property
    def last_modified_by(self):
        if self.LAST_MODIFIED_BY in self.metadata:
            return self.metadata[self.LAST_MODIFIED_BY]
        else:
            return None

    @property
    def computed_by(self):
        if self.COMPUTED_BY in self.metadata:
            return self.metadata[self.COMPUTED_BY]
        else:
            return None

    @property
    def execution_time(self):
        if self.EXECUTION_TIME in self.metadata:
            return self.metadata[self.EXECUTION_TIME]
        else:
            return None

    @property
    def dependencies(self):
        if self.DEPENDENCIES in self.metadata:
            return self.metadata[self.DEPENDENCIES]
        else:
            return None

    @property
    def metadata(self):
        return self._metadata

    def merge_metadata(self, metadata: dict):

        for key, value in metadata.items():
            # If the key is missing or key is to be overwritten
            if self.metadata.get(key, None) is None:
                self.metadata[key] = value
            else:
                pass


class TrackedObject(MetadataMixin):
    __metaclass__ = ABCMeta
    """
    Base class for tracked objects with logging functions.
    """

    def __init__(self, _pypads_env: LoggingEnv, **kwargs):
        self._env = _pypads_env

    @abstractmethod
    def write_meta(self, **metadata):
        raise NotImplementedError

    @abstractmethod
    def write_content(self,*args,**kwargs):
        raise NotImplementedError

    def serialize(self,*args,**kwargs):
        raise NotImplementedError
