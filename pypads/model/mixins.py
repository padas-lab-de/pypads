from abc import ABCMeta

from pypads.model.domain import LibraryModel
from pypads.model.metadata import ModelObject


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
