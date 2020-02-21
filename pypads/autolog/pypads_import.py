import importlib
import inspect
import sys
from importlib._bootstrap_external import PathFinder, _LoaderBasics
from logging import warning, info, debug
# noinspection PyUnresolvedReferences
from types import ModuleType

from pypads.autolog.mappings import AlgorithmMapping
from pypads.autolog.wrapping import wrap_module, wrap_class, wrap_function, punched_classes, punched_module


class PyPadsLoader(_LoaderBasics):

    def __init__(self, spec):
        self.spec = spec

    @staticmethod
    def _add_found_class(mapping):
        from pypads.base import get_current_pads
        return get_current_pads().mapping_registry.add_found_class(mapping)

    @staticmethod
    def _get_algorithm_mappings():
        from pypads.base import get_current_pads
        return get_current_pads().mapping_registry.get_relevant_mappings()

    def load_module(self, fullname):
        module = self.spec.loader.load_module(fullname)
        return module

    def create_module(self, spec):
        module = self.spec.loader.create_module(spec)
        return module

    def exec_module(self, module):
        out = self.spec.loader.exec_module(module)

        # On execution of a module we search for relevant mappings
        # TODO we might want to make this configurable/improve performance. This looks at every imported class.
        for name in dir(module):
            reference = getattr(module, name)
            if inspect.isclass(reference) and hasattr(reference, "mro"):
                try:

                    # Look at the MRO and add classes to be punched which inherit from our punched classes
                    overlap = set(reference.mro()[1:]) & punched_classes
                    if bool(overlap):
                        # TODO maybe only for the first one
                        for o in overlap:
                            if reference not in punched_classes:
                                found_mapping = AlgorithmMapping(
                                    reference.__module__ + "." + reference.__qualname__, o._pypads_mapping.library,
                                    o._pypads_mapping.algorithm, o._pypads_mapping.file, o._pypads_mapping.hooks)
                                found_mapping.in_collection = o._pypads_mapping.in_collection
                                self._add_found_class(mapping=found_mapping)
                except Exception as e:
                    debug("Skipping superclasses of " + str(reference) + ". " + str(e))

        # TODO And every mapping.
        for mapping in self._get_algorithm_mappings():
            if mapping.reference.startswith(module.__name__):
                if mapping.reference == module.__name__:
                    wrap_module(module, mapping)
                else:
                    ref = mapping.reference
                    path = ref[len(module.__name__) + 1:].rsplit(".")
                    obj = module
                    ctx = obj
                    for seg in path:
                        try:
                            ctx = obj
                            obj = getattr(obj, seg)
                        except AttributeError:
                            obj = None
                            break

                    if obj:
                        if inspect.isclass(obj):
                            if mapping.reference == obj.__module__ + "." + obj.__name__:
                                wrap_class(obj, ctx, mapping)

                        elif inspect.isfunction(obj):
                            wrap_function(obj.__name__, ctx, mapping)
        return out


class PyPadsFinder(PathFinder):
    """
    Import lib extension. This finder provides a special loader if mapping files contain the object.
    """

    def find_spec(cls, fullname, path=None, target=None):
        if fullname not in sys.modules:
            path_ = sys.meta_path[
                    [i for i in range(len(sys.meta_path)) if isinstance(sys.meta_path[i], PyPadsFinder)].pop() + 1:]
            i = iter(path_)
            spec = None
            try:
                # Find a valid importer for the given fullname on the meta_path
                importer = None
                while not spec:
                    importer = next(i)
                    if hasattr(importer, "find_spec"):
                        spec = importer.find_spec(fullname, path)

                # Use the importer as a real importer but wrap it in the PyPadsLoader
                if spec and importer:
                    spec.loader = PyPadsLoader(importer.find_spec(fullname, path))
                    return spec
            except StopIteration:
                pass


active = False
is_recursive = False


def extend_import_module():
    """
    Function to add the custom import logic to the python importlib execution
    :return:
    """
    path_finder = [i for i in range(len(sys.meta_path)) if
                   "_frozen_importlib_external.PathFinder" in str(sys.meta_path[i])]
    sys.meta_path.insert(path_finder.pop(), PyPadsFinder())


def activate_tracking(mod_globals=None):
    """
    Function to duck punch all objects defined in the mapping files. This should at best be called before importing
    any libraries.
    :param mod_globals: globals() object used to duckpunch already loaded classes
    :return:
    """
    global active
    if not active:
        active = True

        # Add our loader to the meta_path
        extend_import_module()

        # Try to punch if we already imported modules before starting to track
        from pypads.base import get_current_pads

        # TODO cleanup the mapping reference rsplit checks
        for i in set(mapping.reference.rsplit('.', 1)[0] for mapping in
                     get_current_pads().mapping_registry.get_algorithms() if
                     mapping.reference.rsplit('.', 1)[0] in sys.modules
                     and mapping.reference.rsplit('.', 1)[0] not in punched_module):
            spec = importlib.util.find_spec(i)
            loader = PyPadsLoader(spec)
            module = loader.load_module(i)
            loader.exec_module(module)
            sys.modules[i] = module
            warning(i + " was imported before PyPads. PyPads has to be imported before importing tracked libraries."
                        " Otherwise it can only try to wrap classes on global level.")
            if mod_globals:
                for k, l in mod_globals.items():
                    if isinstance(l, ModuleType) and i in str(l):
                        mod_globals[k] = module
                    elif inspect.isclass(l) and i in str(l) and hasattr(module, l.__name__):
                        if k not in mod_globals:
                            warning(i + " was imported before PyPads, but couldn't be modified on globals.")
                        else:
                            info("Modded " + i + " after importing it. This might fail.")
                            mod_globals[k] = getattr(module, l.__name__)
