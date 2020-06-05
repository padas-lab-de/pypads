import inspect
import re
import sys
import types
from functools import wraps
from importlib._bootstrap_external import PathFinder
# noinspection PyUnresolvedReferences
from multiprocessing import Value

from pypads import logger
from pypads.autolog.mappings import PadsMapping
from pypads.autolog.wrapping.base_wrapper import Context


def _add_found_class(mapping):
    from pypads.pypads import get_current_pads
    return get_current_pads().mapping_registry.add_found_class(mapping)


def _get_relevant_mappings(module):
    from pypads.pypads import get_current_pads
    return get_current_pads().mapping_registry.get_relevant_mappings(module)


def _add_inherited_mapping(clazz, super_class):
    from pypads.pypads import get_current_pads
    if clazz.__name__ not in get_current_pads().wrap_manager.class_wrapper.punched_class_names:
        if hasattr(super_class, "_pypads_mapping_" + super_class.__name__):
            for mapping in getattr(super_class, "_pypads_mapping_" + super_class.__name__):
                found_mapping = PadsMapping(
                    clazz.__module__ + "." + clazz.__qualname__, mapping.library,
                    mapping.in_collection, mapping.events, mapping.values)
                _add_found_class(mapping=found_mapping)


def duck_punch_loader(spec):
    if not spec.loader:
        return spec

    original_exec = spec.loader.exec_module

    @wraps(original_exec)
    def exec_module(self, module, execute=original_exec):
        out = execute(module)

        # History to check if a class inherits a wrapping intra-module
        mro_entry_history = {}

        def _find_wrappees(segments, ctx, obj, mapping, current_pads):
            if len(segments) > 0:
                segment = segments.pop(0)
                if segment.startswith("{re:"):
                    regex = segment[1:-1]
                    objs = [var for var in dir(obj) if re.match(regex, var)]
                    for o in objs:
                        _find_wrappees(segments, obj, o, mapping, current_pads)
                else:
                    # Add the normal segments with the regex segments
                    joined_segments = segment.split(".") + segments
                    try:
                        o = getattr(obj, joined_segments[0])
                        _find_wrappees(joined_segments[1:], obj, o, mapping, current_pads)
                    except AttributeError:
                        pass
            else:
                if inspect.isclass(obj):
                    current_pads.wrap_manager.wrap(obj, Context(ctx), mapping)
                    if obj in mro_entry_history:
                        for clazz in mro_entry_history[obj]:
                            _add_inherited_mapping(clazz, obj)

                elif inspect.isfunction(obj) or 'wrapper_descriptor' in str(obj.__class__):
                    current_pads.wrap_manager.wrap(obj, Context(ctx), mapping)

        from pypads.pypads import current_pads
        if current_pads:
            # TODO we might want to make this configurable/improve performance.
            #  This looks at every imported class and every mapping.
            # On execution of a module we search for relevant mappings
            # For every var on module
            for name in dir(module):
                reference = getattr(module, name)
                if inspect.isclass(reference) and hasattr(reference, "mro"):
                    try:

                        # Look at the MRO and add classes to be punched which inherit from our punched classes
                        mro_ = reference.mro()[1:]
                        for entry in mro_:
                            if entry not in mro_entry_history.keys():
                                mro_entry_history[entry] = [reference]
                            else:
                                mro_entry_history[entry].append(reference)
                        overlap = set(
                            [c.__name__ for c in mro_]) & current_pads.wrap_manager.class_wrapper.punched_class_names
                        if bool(overlap):
                            # TODO Is one inherited mapping maybe enough? Only add for the first one?
                            for o in overlap:
                                _add_inherited_mapping(reference, o)
                    except Exception as e:
                        logger.debug("Skipping superclasses of " + str(reference) + ". " + str(e))

            # For every mapping in our mappings
            for mapping in _get_relevant_mappings(module):
                if mapping.is_applicable(module.__name__):
                    current_pads.wrap_manager.wrap(module, None, mapping)
                else:
                    ref = mapping.reference
                    path = ref[len(module.__name__) + 1:]

                    obj = module

                    # split for regex
                    segments = re.split(r"(\{.*?\})", path)
                    _find_wrappees(segments, module, obj, mapping, current_pads)
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
