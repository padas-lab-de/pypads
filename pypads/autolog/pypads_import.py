import inspect
import sys
import types
from functools import wraps
from importlib._bootstrap_external import PathFinder
# noinspection PyUnresolvedReferences
from multiprocessing import Value

from pypads import logger
from pypads.autolog.mappings import PadsMapping, MappingHit, _to_segments
from pypads.autolog.wrapping.base_wrapper import Context


def _add_found_class(mapping):
    from pypads.pypads import get_current_pads
    return get_current_pads().mapping_registry.add_found_class(mapping)


def _get_relevant_mappings(segments, search_found):
    from pypads.pypads import get_current_pads
    return get_current_pads().mapping_registry.get_relevant_mappings(segments, search_found)


def _add_inherited_mapping(clazz, super_class):
    from pypads.pypads import get_current_pads
    if clazz.__name__ not in get_current_pads().wrap_manager.class_wrapper.punched_class_names:
        if hasattr(super_class, "_pypads_mapping_" + super_class.__name__):
            for mapping_hit in getattr(super_class, "_pypads_mapping_" + super_class.__name__):
                found_mapping = PadsMapping(
                    ".".join(filter(lambda s: len(s) > 0,
                                    [clazz.__module__, clazz.__qualname__,
                                     ".".join([h.serialize() for h in
                                               mapping_hit.mapping.segments[len(mapping_hit.segments):]])])),
                    mapping_hit.mapping.library,
                    mapping_hit.mapping.in_collection, mapping_hit.mapping.events, mapping_hit.mapping.values)
                _add_found_class(found_mapping)


def duck_punch_loader(spec):
    if not spec.loader:
        return spec

    original_exec = spec.loader.exec_module

    @wraps(original_exec)
    def exec_module(self, module, execute=original_exec):
        out = execute(module)

        # History to check if a class inherits a wrapping intra-module
        mro_entry_history = {}

        from pypads.pypads import current_pads
        reference = module.__name__

        if current_pads:
            # TODO we might want to make this configurable/improve performance.
            #  This looks at every imported class and every mapping.
            # On execution of a module we search for relevant mappings
            # For every var on module
            for name in dir(module):
                obj = getattr(module, name)

                if obj is not None:
                    obj_ref = ".".join([reference, name])
                    obj_seg = _to_segments(obj_ref)

                    # Skip modules if they are from another package for now
                    if inspect.ismodule(obj):
                        if not module.__name__.split(".")[0] == obj.__name__.split(".")[0]:
                            continue

                    if inspect.isclass(obj) and hasattr(obj, "mro"):
                        found = []
                        try:

                            # Look at the MRO and add classes to be punched which inherit from our punched classes
                            mro_ = obj.mro()[1:]
                            for entry in mro_:
                                if entry not in mro_entry_history.keys():
                                    mro_entry_history[entry] = [obj]
                                else:
                                    mro_entry_history[entry].append(obj)
                                if hasattr(entry, "_pypads_mapping_" + entry.__name__):
                                    _add_inherited_mapping(obj, entry)
                                    found.append(entry)
                        except Exception as e:
                            logger.debug("Skipping some superclasses of " + str(obj) + ". " + str(e))
                        mappings = _get_relevant_mappings(obj_seg, len(found) > 0)
                    else:
                        mappings = _get_relevant_mappings(obj_seg, False)

                    for mapping in mappings:
                        current_pads.wrap_manager.wrap(obj, Context(module, reference), MappingHit(mapping, obj_seg))
        return out

    spec.loader.exec_module = types.MethodType(exec_module, spec.loader)
    return spec


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
                if spec and importer and spec.loader:
                    return duck_punch_loader(spec)
            except StopIteration:
                pass


def extend_import_module():
    """
    Function to add the custom import logic to the python importlib execution
    :return:
    """
    path_finder = [i for i in range(len(sys.meta_path)) if
                   "_frozen_importlib_external.PathFinder" in str(sys.meta_path[i])]
    sys.meta_path.insert(path_finder.pop(), PyPadsFinder())
