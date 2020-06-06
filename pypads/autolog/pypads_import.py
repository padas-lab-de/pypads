import inspect
import re
import sys
import types
from abc import abstractmethod, ABCMeta
from functools import wraps
from importlib._bootstrap_external import PathFinder
# noinspection PyUnresolvedReferences
from multiprocessing import Value

from pypads import logger
from pypads.autolog.mappings import PadsMapping, MappingHit
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
            for mapping_hit in getattr(super_class, "_pypads_mapping_" + super_class.__name__):
                found_mapping = PadsMapping(
                    ".".join(filter(lambda s: len(s) > 0,
                                    [clazz.__module__, clazz.__qualname__,
                                     ".".join([h.serialize() for h in mapping_hit.segments])])),
                    mapping_hit.mapping.library,
                    mapping_hit.mapping.in_collection, mapping_hit.mapping.events, mapping_hit.mapping.values)
                _add_found_class(mapping=found_mapping)


def _to_segments(reference):
    segments = []
    for seg in filter(lambda s: len(s) > 0, re.split(r"(\{.*?\})", reference)):
        if seg.startswith("{re:"):
            segments.append(RegexSegment(seg[4:-1]))
        else:
            segments = segments + [PathSegment(s) for s in filter(lambda s: len(s) > 0, seg.split("."))]
    return segments


class Segment:
    __metaclass__ = ABCMeta

    def __init__(self, content):
        self._content = content

    @property
    def content(self):
        return self._content

    @abstractmethod
    def fits(self, segment):
        raise NotImplementedError

    @abstractmethod
    def serialize(self):
        raise NotImplementedError

    def __str__(self):
        return str(self._content)


class PathSegment(Segment):

    def fits(self, segment):
        return segment == self.content

    def serialize(self):
        return self.content


class RegexSegment(Segment):

    def fits(self, segment):
        return re.match(self.content, segment)

    def serialize(self):
        return "{re:" + self.content + "}"


def duck_punch_loader(spec):
    if not spec.loader:
        return spec

    original_exec = spec.loader.exec_module

    @wraps(original_exec)
    def exec_module(self, module, execute=original_exec):
        out = execute(module)

        # History to check if a class inherits a wrapping intra-module
        mro_entry_history = {}

        def _find_wrappees(segments, ctx, obj, mapping, current_pads, curr_segment=None):

            if inspect.isclass(obj):
                current_pads.wrap_manager.wrap(obj, ctx, MappingHit(mapping, segments))
                if obj in mro_entry_history:
                    for clazz in mro_entry_history[obj]:
                        _add_inherited_mapping(clazz, obj)
            elif inspect.isfunction(obj):
                current_pads.wrap_manager.wrap(obj, ctx, MappingHit(mapping, [
                                                                                 curr_segment] + segments if curr_segment is not None else segments))

            if len(segments) > 0:
                curr_segment = segments[0]
                if isinstance(curr_segment, RegexSegment):
                    objs = [var for var in dir(obj) if curr_segment.fits(var)]
                    sub_segments = segments[1:]
                    for name in objs:
                        _find_wrappees(sub_segments, Context(obj, ctx.reference + "." + name), getattr(obj, name),
                                       mapping,
                                       current_pads, curr_segment=curr_segment)
                else:
                    # Add the normal segments with the regex segments
                    try:
                        if hasattr(obj, curr_segment.content):
                            o = getattr(obj, curr_segment.content)
                        else:
                            o = obj[curr_segment.content]
                        sub_segments = segments[1:]
                        _find_wrappees(sub_segments, Context(obj, ctx.reference + "." + o.__name__), o, mapping,
                                       current_pads, curr_segment=curr_segment)
                    except Exception as e:
                        pass

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
                            if hasattr(entry, "_pypads_mapping_" + entry.__name__):
                                _add_inherited_mapping(reference, entry)
                    except Exception as e:
                        logger.debug("Skipping superclasses of " + str(reference) + ". " + str(e))

            # For every mapping in our mappings
            for mapping in _get_relevant_mappings(module):
                if mapping.is_applicable(None, module):
                    current_pads.wrap_manager.wrap(module, None, mapping)
                else:
                    segments = _to_segments(mapping.reference)
                    entry_segs = module.__name__.split(".")
                    checks = []
                    for i, entry_seg in enumerate(entry_segs):
                        checks.append(len(segments) >= len(entry_segs) and segments[i].fits(entry_seg))
                    if all(checks):
                        _find_wrappees(segments[len(checks):], Context(sys.modules, module.__name__), module, mapping,
                                       current_pads, curr_segment=segments[len(checks)])
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
