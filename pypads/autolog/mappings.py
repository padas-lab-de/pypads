import glob
import os
import re
from abc import ABCMeta, abstractmethod
from itertools import chain
from os.path import expanduser
from typing import List

import yaml

from pypads import logger

mapping_files = glob.glob(expanduser("~") + ".pypads/bindings/**.yml")
mapping_files.extend(
    glob.glob(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/bindings/resources/mapping/**.yml>"))


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

    def __hash__(self):
        return hash(self.content)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.fits(other)
        return self.content == other.content


class PathSegment(Segment):

    def fits(self, segment):
        return segment == self.content

    def serialize(self):
        return self.content

    def __str__(self):
        return self.serialize()


class RegexSegment(Segment):

    def fits(self, segment):
        return re.match(self.content, segment)

    def serialize(self):
        return "{re:" + self.content + "}"

    def __str__(self):
        return self.serialize()


def _to_segments(reference):
    segments = []
    for seg in filter(lambda s: len(s) > 0, re.split(r"(\{.*?\})", reference)):
        if seg.startswith("{re:"):
            segments.append(RegexSegment(seg[4:-1]))
        else:
            segments = segments + [PathSegment(s) for s in filter(lambda s: len(s) > 0, seg.split("."))]
    return segments


class PadsMapping:
    """
    Mapping for an algorithm defined by a pypads mapping file
    """

    def __init__(self, reference, library, in_collection, events, values):
        self._library = library
        self._in_collection = in_collection
        self._values = values
        self._events = events

        self._segments = _to_segments(reference)

    def is_applicable(self, ctx, obj):
        if not hasattr(obj, "__name__"):
            return False
        reference = ctx.reference + "." + obj.__name__ if ctx is not None else obj.__name__
        if self.reference == reference:
            return True
        segments = _to_segments(reference)
        offset = len(segments) - 1
        if offset >= len(self.segments):
            return False
        return self.segments[offset].fits(segments[offset].content)

    def applicable_filter(self, ctx):
        """
        Create a filter to check if the mapping is applicable
        :param ctx:
        :param mapping:
        :return:
        """

        def mapping_applicable_filter(name):
            if hasattr(ctx.container, name):
                try:
                    return self.is_applicable(ctx, getattr(ctx.container, name))
                except RecursionError as rerr:
                    logger.error("Recursion error on '" + str(
                        ctx) + "'. This might be because __get_attr__ is being wrapped. " + str(rerr))
            else:
                logger.debug("Can't access attribute '" + str(name) + "' on '" + str(ctx) + "'. Skipping.")
            return False

        return mapping_applicable_filter

    @property
    def in_collection(self):
        return self._in_collection

    @in_collection.setter
    def in_collection(self, value):
        self._in_collection = value

    @property
    def reference(self):
        return ".".join([s.serialize() for s in self._segments])

    @property
    def library(self):
        return self._library

    @property
    def events(self):
        return self._events

    @property
    def values(self):
        return self._values

    @property
    def segments(self):
        return self._segments

    def __str__(self):
        return "Mapping[" + str(self.reference) + ", lib=" + str(self.library) + "]"

    def __eq__(self, other):
        return self.reference == other.reference and self.events == other.events

    def __hash__(self):
        return hash((self.reference, "|".join(self.events)))


class MappingCollection:
    def __init__(self, key, version, lib, lib_version):
        self._mappings = {}
        self._name = key
        self._version = version
        self._lib = lib
        self._lib_version = lib_version

    @property
    def version(self):
        return self._version

    @property
    def lib(self):
        return self._lib

    @property
    def lib_version(self):
        return self._lib_version

    @property
    def name(self):
        return self._name

    @property
    def mappings(self):
        return self._mappings

    def add_mapping(self, mapping):
        path_map = self._mappings
        for segment in mapping.segments:
            if segment not in path_map:
                path_map[segment] = dict()
            path_map = path_map[segment]
        if ":mapping" not in path_map:
            path_map[":mapping"] = []
        path_map[":mapping"].append(mapping)

    def _get_all_mappings(self, current_path=None):
        mappings = []
        if current_path is None:
            current_path = self._mappings
        for k, v in current_path.items():
            if isinstance(k, str) and ":mapping" == k:
                mappings = mappings + v
            else:
                if isinstance(v, dict):
                    mappings = mappings + self._get_all_mappings(current_path=v)
        return mappings

    def find_mappings(self, segments, current_path=None):
        mappings = []
        if current_path is None:
            current_path = self._mappings
        if len(segments) > 0:
            if segments[0] in current_path:
                mappings = mappings + self.find_mappings(segments[1:], current_path[segments[0]])

            # For non PathSegments we can't use the hash lookup
            for s, v in current_path.items():
                if isinstance(s, RegexSegment) and s.fits(segments[0].content):
                    mappings = mappings + self.find_mappings(segments[1:], v)
        else:
            mappings = mappings + self._get_all_mappings(current_path)

        return mappings


class MappingSchema:

    def __init__(self, fragments, metadata, reference, events, values):
        self._fragments = fragments
        self._metadata = metadata
        self._reference = reference
        self._events = events
        self._values = values

    @property
    def fragments(self):
        return self._fragments

    @property
    def metadata(self):
        return self._metadata

    @property
    def reference(self):
        return self._reference

    @property
    def values(self):
        return self._values

    @property
    def events(self):
        return self._events

    def get(self, key):
        return self._values[key]

    def has(self, key):
        return key in self._values


class SerializedMapping(MappingCollection):

    def __init__(self, key, content):
        yml = yaml.load(content, Loader=yaml.SafeLoader)
        schema = MappingSchema(yml["fragments"] if "fragments" in yml else [], yml["metadata"], "", set(), {})
        super().__init__(key, schema.metadata["version"], schema.metadata["library"]["name"],
                         schema.metadata["library"]["version"])
        self._build_mappings(yml["mappings"], schema, True)

    def _build_mappings(self, node, schema: MappingSchema, entry):
        _fragments = []
        _children = []
        _events = set()
        _values = {}
        mappings = {}

        # replace fragments
        for k, v in node.items():
            if entry:
                _children.append((k, v))
            elif k.startswith("::"):
                _fragments.append(k[2:])
            elif k.startswith("."):
                _children.append((k, v))
            elif k == "events":
                if isinstance(v, str):
                    _events.add(v)
                elif isinstance(v, List):
                    for event in v:
                        _events.add(event)
            elif k == "data":
                _values[k] = v

        for p in _fragments:
            for k, v in schema.fragments[p].items():
                node[k] = v
            del node["::" + p]

        schema = MappingSchema(schema.fragments, schema.metadata, reference=schema.reference,
                               events=_events.union(schema.events),
                               values={**schema.values, **_values})

        if len(_fragments) > 0:
            mappings = {**mappings, **self._build_mappings(node, schema, False)}
        else:
            if len(_children) > 0:
                for c, v in _children:
                    mappings = {**mappings, **self._build_mappings(v, MappingSchema(schema.fragments, schema.metadata,
                                                                                    reference=schema.reference + c,
                                                                                    events=schema.events,
                                                                                    values=schema.values), False)}
            else:
                self.add_mapping(
                    PadsMapping(schema.reference, schema.metadata["library"], self, schema.events, schema.values))
        return mappings


class MappingFile(SerializedMapping):

    def __init__(self, path, name=None):
        with open(path) as f:
            if name is None:
                name = os.path.basename(f.name)
            data = f.read()
        super().__init__(name, data)


class MappingRegistry:
    """
    Class holding all the mappings
    """

    def __init__(self, *paths):

        self._mappings = {}
        self._found_mappings = MappingCollection("found", None, None, None)

        for path in paths:
            self.load_mapping(path)

    def add_mapping(self, mapping: MappingCollection, key=None):

        if key is None and isinstance(mapping, MappingFile):
            key = mapping.name

        if key is None:
            logger.error(
                "Couldn't add mapping " + str(mapping) + " to the pypads mapping registry. Lib or key are undefined.")
        else:
            self._mappings[key] = mapping

    def load_mapping(self, path):
        self.add_mapping(MappingFile(path))

    def add_found_class(self, mapping):
        self._found_mappings.add_mapping(mapping)

    def iter_found_mappings(self, segments):
        return self._found_mappings.find_mappings(segments)

    def get_libraries(self):
        all_libs = set()
        for key, mapping in self._mappings.items():
            all_libs.add(mapping.lib)
        return all_libs

    def get_relevant_mappings(self, segments, search_found):
        """
        Function to find all relevant mappings. This produces a generator getting extended with found subclasses
        :return:
        """
        if search_found:
            return set(chain(self.get_static_mappings(segments), self.iter_found_mappings(segments)))
        else:
            return set(self.get_static_mappings(segments))

    def get_static_mappings(self, segments):
        """
        Get all mappings defined in all mapping files.
        :return:
        """
        mappings = []
        for k, collection in self._mappings.items():
            for m in collection.find_mappings(segments):
                mappings.append(m)
        return mappings


class MappingHit:

    def __init__(self, mapping: PadsMapping, segments):
        self._segments = segments
        self._mapping = mapping

    @property
    def segments(self):
        return self._segments

    @property
    def mapping(self):
        return self._mapping
