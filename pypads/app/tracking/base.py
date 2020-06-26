import os
from abc import ABCMeta, abstractmethod
from typing import Any

from pypads import logger
from pypads.app.injections.base_logger import LoggingFunction
from pypads.app.misc.mixins import MetadataMixin, DefensiveCallableMixin, DependencyMixin
from pypads.injections.analysis.call_tracker import LoggingEnv
# noinspection PyUnusedLocal,PyShadowingNames,PyProtectedMember
from pypads.utils.logging_util import WriteFormats
from pypads.utils.util import inheritors


class TrackingObjectMixin(MetadataMixin):
    """
    Base class for tracking objects with pypads.
    """
    # default attributes
    _path_suffix = None

    # Default storage attributes
    PATH = "Tracking Objects"
    META_FORMAT = WriteFormats.yaml
    CONTENT_FORMAT = WriteFormats.json

    # Metadata attributes
    SOURCE = "source"
    PROCESS = 'process'
    THREAD = 'thread'
    DATA = 'data'

    def __init__(self, *args, source = None, metadata=None, **kwargs):
        if source:
            metadata = {**{self.SOURCE: str(source)}, **metadata}
        self._data = []
        super().__init__(*args, metadata=metadata, **kwargs)

    @property
    def data(self):
        return self._data

    @property
    def path_suffix(self):
        if self._path_suffix:
            return self._path_suffix
        else:
            return ""

    def add_runtime(self, label, time):
        self.metadata[label] = time

    def to_name(self):
        return str(self.id)

    def set_suffix(self, suffix):
        self._path_suffix = suffix

    def to_folder(self):
        return os.path.join(self.PATH, self.path_suffix, self.to_name())

    def to_path(self, obj_name):
        return os.path.join(self.to_folder(), obj_name)

    def to_meta_path(self):
        return self.to_path("metadata")

    @abstractmethod
    def write_data(self, name, obj, path_prefix=None, data_format=None):
        raise NotImplementedError

    @abstractmethod
    def store(self, ):
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, *args, **kwargs):
        raise NotImplementedError


class LoggerTrackingObject(TrackingObjectMixin):
    """
    Base class for tracking objects with logging functions.
    """
    # Metadata attributes
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

    def __init__(self, *args, _pypads_env: LoggingEnv, metadata=None, schema=None,
                 **kwargs):
        if metadata is None:
            metadata = dict()
        self._call = _pypads_env.call.call_id

        metadata = {
            **{self.PROCESS: self._call.process, self.THREAD: self._call.thread,
               self.CONTEXT: self._call.context.container.__name__, self.INSTANCE: self._call.instance_number,
               self.CALL: self._call.call_number, self.COMPUTED_BY: self._call.wrappee.__name__}, **metadata}

        super().__init__(*args, metadata=metadata, schema=schema, **kwargs)

    @property
    def computed_by(self):
        return self._call.wrappee.__name__

    @property
    def execution_time(self):
        return self.metadata.get(self.EXECUTION_TIME, None)

    def to_name(self):
        return '.'.join([self._call.context.container.__name__, self._call.wrappee.__name__, str(self.id)])

    def store(self):
        meta = {self.DATA: []}
        for item in self.data:
            self.pads.api.write_data_item(item.get("name"), item.get("object"), data_format=item.get("format"))
            meta.get(self.DATA).append(item.get("name"))

        # Add content metadata
        self.merge_metadata(metadata=meta)

        # Write the metadata
        self.pads.api.write_tracking_object_meta(self.to_meta_path(), self.metadata)


class TrackingObjectFactory(DefensiveCallableMixin):
    """
    Class creating a managed tracking object. A tracking object is used to store loggers output in a defined structure.
    """

    def __init__(self, pads, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pads = pads

    def _handle_error(self, *args, ctx, _pypads_env, error, **kwargs):
        logger.warning("Couldn't initialize tracking object because of exception: {0}".format(error))

    def __real_call__(self, ctx, *args, source: Any = None, object_class=TrackingObjectMixin, **kwargs):
        return object_class(*args, source= source, pads=self.pads, **kwargs)


def get_tracked_objects():
    """
    Find all tracking objects defined in our imported context.
    :return:
    """
    return inheritors(TrackingObjectMixin)