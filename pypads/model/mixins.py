from abc import ABCMeta

from pypads.model.domain import LibraryModel
from pypads.model.metadata import ModelObject
from pypads.utils.util import persistent_hash


class ProvenanceMixin(ModelObject, metaclass=ABCMeta):
    """
    Class extracting its library reference automatically if possible.
    """

    def __init__(self, *args, lib_model: LibraryModel = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.defined_in = None
        if lib_model is None:
            self._defined_in = get_library_descriptor(self)
        else:
            self._defined_in = lib_model

    def model(self, force=False, validate=True, include=None):
        self.store_lib()
        return super().model(force=force, validate=validate, include=include)

    def store_lib(self):
        from pypads.app.pypads import get_current_pads
        lib_repo = get_current_pads().library_repository
        # TODO get hash uid for logger
        lib_hash = persistent_hash((self._defined_in.name, self._defined_in.version))
        if not lib_repo.has_object(uid=lib_hash):
            lib_obj = lib_repo.get_object(uid=lib_hash)
            lib_obj.log_json(self._defined_in)
        else:
            lib_obj = lib_repo.get_object(uid=lib_hash)
        self.defined_in = lib_obj.get_reference()


def get_library_descriptor(obj) -> LibraryModel:
    """
    Try to extract the defining package of this class.
    :return:
    """
    # TODO extract reference to self package
    try:
        name = obj.__module__.split(".")[0]
        from pypads.utils.util import find_package_version
        version = find_package_version(name)
        return LibraryModel(name=name, version=version, uid=persistent_hash((name, version)), extracted=True)
    except Exception:
        return LibraryModel(name="__unkown__", version="0.0", uid=persistent_hash(("__unkown__", "0.0")),extracted=True)
