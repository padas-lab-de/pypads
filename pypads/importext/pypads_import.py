import inspect
import sys
import types
from collections import OrderedDict
from functools import wraps
from typing import Set

from importlib._bootstrap_external import PathFinder
# noinspection PyUnresolvedReferences
from multiprocessing import Value

from pypads import logger
from pypads.importext.mappings import Mapping, MatchedMapping
from pypads.importext.package_path import PackagePath, PackagePathMatcher, Package
from pypads.importext.wrapping.base_wrapper import Context


def _add_found_class(mapping):
    from pypads.app.pypads import get_current_pads
    return get_current_pads().mapping_registry.add_found_class(mapping)


def _get_relevant_mappings(package: Package):
    from pypads.app.pypads import get_current_pads
    return get_current_pads().mapping_registry.get_relevant_mappings(package)


def _get_hooked_on_import_fns(matched_mappings: Set[MatchedMapping]):
    """
    For a given module find the hook functions defined in a mapping and configured in a configuration to be executed on import.
    :param mapping:
    :return:
    """
    from pypads.app.pypads import get_current_pads
    current_pads = get_current_pads()
    fns = []
    import_hooks = set()
    for matched_mapping in matched_mappings:
        for hook in matched_mapping.mapping.import_hooks:
            import_hooks.add(hook)

    for hook in import_hooks:
        fns = fns + current_pads.hook_registry.get_logging_functions(hook)
    return fns


def _add_inherited_mapping(clazz, super_class):
    from pypads.app.pypads import get_current_pads
    found_mappings = set()
    if clazz.__name__ not in get_current_pads().wrap_manager.class_wrapper.punched_class_names:
        if hasattr(super_class, "_pypads_mapping_" + super_class.__name__):
            for matched_mapping in getattr(super_class, "_pypads_mapping_" + super_class.__name__):
                """
                Build the package path matcher by looking at the superclass matched_mappings and deconstructing the 
                package_path of it. Taking from the matcher unmatched parts and adding them to the module and qualname.
                """
                found_mapping = Mapping(PackagePathMatcher(
                    ".".join(filter(lambda s: len(s) > 0,
                                    [clazz.__module__, clazz.__qualname__,
                                     ".".join([h.serialize() for h in
                                               matched_mapping.mapping.matcher.matchers[
                                               len(matched_mapping.package_path.segments):]])]))),
                    matched_mapping.mapping.in_collection, {h.anchor for h in matched_mapping.mapping.hooks},
                    matched_mapping.mapping.values, inherited=matched_mapping.mapping)
                found_mappings.add(found_mapping)
    return found_mappings


# import logging fns queue per module
_import_loggers_queues = OrderedDict()
# delayed wrappings for modules with triggered import logging functions
_wrapping_queues = OrderedDict()


def has_delayed_wrapping():
    return len(_import_loggers_queues.keys()) > 0


def add_on_import_hooks(module):
    """
    Function that search for on-import logging hooks for the module in question.
    :param module:
    """
    from pypads.app.pypads import current_pads
    reference = module.__name__

    if current_pads:
        # Package path on module __init__ for the on-import hooks
        _package = Package(module, PackagePath(".".join([reference, "__init__"])))
        # looking for existing mappings relevant to __init__ of the module
        _mappings = _get_relevant_mappings(_package)

        if len(_mappings) > 0:
            # Getting the import logger matching the hooks
            fns = _get_hooked_on_import_fns({MatchedMapping(mapping, _package.path) for mapping in _mappings})
            if len(fns) > 0 and reference not in _import_loggers_queues:
                _import_loggers_queues.update({reference: []})
            for (fn, config) in fns:
                _import_loggers_queues[reference].append((fn, config))


def add_wrappings(self, module):
    """
    Function that look for matched mappings and inject corresponding logging functionalities

    :param self: context
    :param module: module to be wrapped
    """
    from pypads.app.pypads import current_pads
    reference = module.__name__

    # History to check if a class inherits a wrapping intra-module
    mro_entry_history = {}

    if current_pads:
        # TODO we might want to make this configurable/improve performance.
        #  This looks at every imported class and every mapping.
        # On execution of a module we search for relevant mappings
        # For every var on module
        try:
            members = inspect.getmembers(module,
                                         lambda x: hasattr(x, "__module__") and x.__module__ == module.__name__)
        except Exception as e:
            logger.debug(
                "getmembers of inspect failed on module '" + str(module.__name__) + "' with expection" + str(
                    e) + ". Falling back to dir to get the members of the module.")
            members = [(name, getattr(module, name)) for name in dir(module)]

        for name, obj in members:
            if obj is not None:
                obj_ref = ".".join([reference, name])
                package = Package(module, PackagePath(obj_ref))

                # Skip modules if they are from another package for now
                if inspect.ismodule(obj):
                    if not module.__name__.split(".")[0] == obj.__name__.split(".")[0]:
                        continue

                mappings = set()
                if inspect.isclass(obj) and hasattr(obj, "mro"):
                    try:

                        # Look at the MRO and add classes to be punched which inherit from our punched classes
                        mro_ = obj.mro()[1:]
                        for entry in mro_:
                            if entry not in mro_entry_history.keys():
                                mro_entry_history[entry] = [obj]
                            else:
                                mro_entry_history[entry].append(obj)
                            if hasattr(entry, "_pypads_mapping_" + entry.__name__):
                                found_mappings = _add_inherited_mapping(obj, entry)
                                mappings = mappings.union(found_mappings)
                    except Exception as e:
                        logger.debug("Skipping some superclasses of " + str(obj) + ". " + str(e))
                mappings = mappings.union(_get_relevant_mappings(package))
                if len(mappings) > 0:
                    if not has_delayed_wrapping():
                        current_pads.wrap_manager.wrap(obj, Context(module, reference),
                                                       {MatchedMapping(mapping, package.path) for mapping in
                                                        mappings})
                    else:
                        _first_in_queue = list(_import_loggers_queues.keys())[0]
                        if not _first_in_queue in _wrapping_queues:
                            _wrapping_queues[_first_in_queue] = []
                        _wrapping_queues[_first_in_queue].append((obj, Context(module, reference),
                                                                  {MatchedMapping(mapping, package.path)
                                                                   for mapping in mappings}))

        if reference in _import_loggers_queues:
            # execute import logger of this reference
            while len(_import_loggers_queues[reference]) > 0:
                (fn, config) = _import_loggers_queues[reference].pop()
                fn(self)
            del _import_loggers_queues[reference]
            if reference in _wrapping_queues:
                for (obj, ctx, mm) in _wrapping_queues[reference]:
                    current_pads.wrap_manager.wrap(obj, ctx, mm)
                del _wrapping_queues[reference]

        if reference in current_pads.wrap_manager.module_wrapper.punched_module_names:
            logger.info(f"PyPads wrapped functions of module {reference}.")


def duck_punch_loader(spec):
    if not spec.loader:
        return spec

    original_exec = spec.loader.exec_module

    @wraps(original_exec)
    def exec_module(self, module, execute=original_exec):
        add_on_import_hooks(module)

        out = execute(module)

        add_wrappings(self, module)

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
