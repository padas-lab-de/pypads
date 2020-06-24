import os
from abc import ABCMeta, abstractmethod

from pypads import logger
from pypads.app.injections.base_logger import LoggingFunction
from pypads.app.misc.mixins import MetadataMixin, DefensiveCallableMixin, DependencyMixin
from pypads.injections.analysis.call_tracker import LoggingEnv
# noinspection PyUnusedLocal,PyShadowingNames,PyProtectedMember
from pypads.utils.logging_util import WriteFormats


class TrackingObject(MetadataMixin):
    __metaclass__ = ABCMeta
    """
    Base class for tracking objects with logging functions.
    """
    # Metadata attributes
    PROCESS = 'process'
    THREAD = 'thread'
    CONTEXT = 'context'
    INSTANCE = 'instance'
    CALL = 'call'
    COMPUTED_BY = 'computed_by'
    EXECUTION_TIME = 'execution_time'
    TRACKED_BY = 'tracked_by'
    LOGGER_ID = 'logger_id'
    PRE_TIME = "pre_time"
    POST_TIME = "post_time"
    LOGGING_TIME = 'logging_time'

    # Storage attributes
    PATH = ""
    META_FORMAT = WriteFormats.yaml
    CONTENT_FORMAT = WriteFormats.text
    SUFFIX = None

    def __init__(self, *args, _pypads_env: LoggingEnv = None, metadata=None, pads=None,
                 **kwargs):
        if metadata is None:
            metadata = dict()
        if _pypads_env:
            self._call = _pypads_env.call.call_id

            metadata = {
                **{self.PROCESS: self._call.process, self.THREAD: self._call.thread,
                   self.CONTEXT: self._call.context.container.__name__, self.INSTANCE: self._call.instance_number,
                   self.CALL: self._call.call_number, self.COMPUTED_BY: self._call.wrappee.__name__}, **metadata}
        self._content = []
        super().__init__(*args, metadata=metadata, pads=pads, **kwargs)

    # def to_parent_folder(self):
    #     return os.path.join("process_" + str(self._process) + str(self._thread))
    @property
    def content(self):
        return self._content

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

    def add_runtime(self, key, time):
        if key not in self.metadata:
            self.metadata[key] = time

    def to_name(self):
        if hasattr(self, '_call'):
            return '.'.join([self._call.context.container.__name__, self._call.wrappee.__name__, str(self.id)])
        else:
            return str(self.id)

    def add_suffix(self, suffix):
        self.SUFFIX = suffix

    def to_folder(self):
        return os.path.join(self.PATH, self.SUFFIX, self.to_name())

    def to_path(self, name):
        return os.path.join(self.to_folder(), name)

    @abstractmethod
    def write_meta(self, metadata):
        if metadata:
            self.merge_metadata(metadata)
        path = self.to_path("metadata")
        self.pads.api._write_meta(path,)

    @abstractmethod
    def write_content(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def serialize(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, *args, **kwargs):
        raise NotImplementedError


class TrackingObjectFactory(DefensiveCallableMixin, DependencyMixin):
    """
    Class creating a managed tracking object. A tracking object is used to store loggers output in a defined structure.
    """

    @staticmethod
    def _needed_packages():
        pass

    def __init__(self, pads, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pads = pads

    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        logger.warning("Couldn't initialize tracking object because of exception: {0}".format(error))

    def __real_call__(self, *args, logging_fn: LoggingFunction = None, custom_class=TrackingObject, **kwargs):
        if logging_fn:
            return logging_fn.TRACKINGOBJECT(*args, pads=self.pads, **kwargs)
        return custom_class(*args, pads=self.pads, **kwargs)
