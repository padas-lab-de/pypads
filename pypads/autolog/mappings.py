import glob
import os
from itertools import chain
from os.path import expanduser
from typing import List

import yaml

from pypads import logger
from pypads.autolog.package_path import RegexMatcher, PackagePath, PackagePathMatcher, \
    SerializableMatcher

mapping_files = glob.glob(expanduser("~") + ".pypads/bindings/**.yml")
mapping_files.extend(
    glob.glob(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/bindings/resources/mapping/**.yml>"))


class Mapping:
    """
    Mapping for an algorithm defined by a pypads mapping file
    """

    def __init__(self, matcher: PackagePathMatcher, library, in_collection, events, values):
        self._library = library
        self._in_collection = in_collection
        self._values = values
        self._events = events
        self._matcher = matcher

    def is_applicable(self, ctx, obj):
        if not hasattr(obj, "__name__"):
            return False
        reference = ctx.reference + "." + obj.__name__ if ctx is not None else obj.__name__
        return self._matcher.matches(PackagePath(reference))

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
        return self._matcher.serialize()

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
    def matcher(self):
        return self._matcher

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

    def add_mapping(self, mapping: Mapping):
        path_map = self._mappings
        for segment in mapping.matcher.matchers:
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
                if isinstance(s, RegexMatcher) and s.matches(segments[0]):
                    mappings = mappings + self.find_mappings(segments[1:], v)
        else:
            mappings = mappings + self._get_all_mappings(current_path)

        return mappings


class MappingSchema:

    def __init__(self, fragments, metadata, matcher: PackagePathMatcher, events, values):
        self._fragments = fragments
        self._metadata = metadata
        self._matcher = matcher
        self._events = events
        self._values = values

    @property
    def fragments(self):
        return self._fragments

    @property
    def metadata(self):
        return self._metadata

    @property
    def matcher(self) -> PackagePathMatcher:
        return self._matcher

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
        schema = MappingSchema(yml["fragments"] if "fragments" in yml else [], yml["metadata"], PackagePathMatcher(""),
                               set(), {})
        super().__init__(key, schema.metadata["version"], schema.metadata["library"]["name"],
                         schema.metadata["library"]["version"])
        self._build_mappings(yml["mappings"], schema)

    def _build_mappings(self, node, schema: MappingSchema):
        _fragments = []
        _children = []
        _events = set()
        _values = {}
        mappings = {}

        # replace fragments
        for k, v in node.items():
            if isinstance(k, SerializableMatcher):
                _children.append((k, v))
            elif k.startswith(":"):
                _children.append((PackagePathMatcher.unserialize(k[1:]), v))
            elif k.startswith(";"):
                _fragments.append(k[1:])
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
            del node[";" + p]

        schema = MappingSchema(schema.fragments, schema.metadata, matcher=schema.matcher,
                               events=_events.union(schema.events),
                               values={**schema.values, **_values})

        if len(_fragments) > 0:
            mappings = {**mappings, **self._build_mappings(node, schema)}
        else:
            if len(_children) > 0:
                for matcher, v in _children:
                    if schema.matcher:
                        matcher = schema.matcher + matcher
                    if not isinstance(matcher, PackagePathMatcher):
                        matcher = PackagePathMatcher(matcher)
                    mappings = {**mappings, **self._build_mappings(v, MappingSchema(schema.fragments, schema.metadata,
                                                                                    matcher=matcher,
                                                                                    events=schema.events,
                                                                                    values=schema.values))}
            elif schema.matcher.matchers is not None:
                self.add_mapping(
                    Mapping(schema.matcher, schema.metadata["library"], self, schema.events, schema.values))
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

    def iter_found_mappings(self, package_path: PackagePath):
        return self._found_mappings.find_mappings(package_path.segments)

    def get_libraries(self):
        all_libs = set()
        for key, mapping in self._mappings.items():
            all_libs.add(mapping.lib)
        return all_libs

    def get_relevant_mappings(self, package_path: PackagePath, search_found):
        """
        Function to find all relevant mappings. This produces a generator getting extended with found subclasses
        :return:
        """
        if search_found:
            return set(chain(self.get_static_mappings(package_path), self.iter_found_mappings(package_path)))
        else:
            return set(self.get_static_mappings(package_path))

    def get_static_mappings(self, package_path: PackagePath):
        """
        Get all mappings defined in all mapping files.
        :return:
        """
        mappings = []
        for k, collection in self._mappings.items():
            for m in collection.find_mappings(package_path.segments):
                mappings.append(m)
        return mappings


class MatchedMapping:
    """
    Class to denote a mapping hit. Given mapping matches given package path.
    """

    def __init__(self, mapping: Mapping, package_path: PackagePath):
        self._package_path = package_path
        self._mapping = mapping

    @property
    def package_path(self) -> PackagePath:
        return self._package_path

    @property
    def mapping(self) -> Mapping:
        return self._mapping
