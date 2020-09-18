import os
from abc import ABCMeta

from pypads.model.domain import LibraryModel
from pypads.model.metadata import ModelObject


class PathAwareMixin(ModelObject, metaclass=ABCMeta):

    def __init__(self, parent_path="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parent_path = parent_path

    def get_relative_path(self):
        """
        Get the full relative path
        :return:
        """
        return os.path.join(self.get_dir(), self.get_file_name())

    def get_dir(self):
        """
        Get a file name for a potential representation of the object.
        :return:
        """
        return os.path.join(self._parent_path, self.get_dir_extension())

    def get_dir_extension(self):
        if hasattr(self, "name"):
            return self.name
        if hasattr(self, "uri"):
            ext = self.uri.rsplit('/', 1)[-1]
            return os.sep.join(ext.rsplit('#', 1))
        return self.__class__.__name__

    def get_file_name(self):
        """
        Get a file name for a potential representation of the object.
        :return:
        """
        return str(self.uid) if hasattr(self, "uid") else str(id(self))


class ProvenanceMixin(ModelObject, metaclass=ABCMeta):
    """
    Class extracting its library reference automatically if possible.
    """

    def __init__(self, *args, lib_model: LibraryModel = None, **kwargs):
        super().__init__(*args, **kwargs)
        if lib_model is None:
            setattr(self, "defined_in", self._get_library_descriptor())
        else:
            setattr(self, "defined_in", lib_model)

        if not hasattr(self, "uri") or getattr(self, "uri") is None and hasattr(self, "uid") and hasattr(self, "is_a"):
            setattr(self, "uri", "{}#{}".format(getattr(self, "is_a"), self.uid))

    def _get_library_descriptor(self) -> LibraryModel:
        """
        Try to extract the defining package of this class.
        :return:
        """
        # TODO extract reference to self package
        try:
            name = self.__module__.split(".")[0]
            from pypads.utils.util import find_package_version
            version = find_package_version(name)
            return LibraryModel(name=name, version=version, extracted=True)
        except Exception:
            return LibraryModel(name="__unkown__", version="0.0", extracted=True)
