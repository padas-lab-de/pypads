from typing import Type

from pypads.model.models import MetadataObject, ReferenceObject, LibraryModel


class ProvenanceMixin(MetadataObject):
    """
    Class extracting its library reference automatically if possible.
    """

    def __init__(self, *args, model_cls: Type[ReferenceObject], lib_model: LibraryModel = None, **kwargs):
        super().__init__(*args, model_cls=model_cls, **kwargs)
        if lib_model is None:
            setattr(self, "defined_in", self._get_library_descriptor())
        else:
            setattr(self, "defined_in", lib_model)

        if not hasattr(self, "uri") or getattr(self, "uri") is None:
            setattr(self, "uri", "{}#{}".format(getattr(self, "is_a"), self.uid))

    def _get_library_descriptor(self) -> LibraryModel:
        # TODO extract reference to self package
        try:
            name = self.__module__.split(".")[0]
            from pypads.utils.util import find_package_version
            version = find_package_version(name)
            return LibraryModel(name=name, version=version)
        except Exception:
            return LibraryModel(name="__unkown__", version="0.0")
