import glob
import os
import re
from itertools import chain
from os.path import expanduser
from typing import List

import yaml

from pypads import logger

mapping_files = glob.glob(expanduser("~") + ".pypads/bindings/**.yml")
mapping_files.extend(
    glob.glob(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/bindings/resources/mapping/**.yml>"))


class PadsMapping:
    """
    Mapping for an algorithm defined by a pypads mapping file
    """

    def __init__(self, reference, library, in_collection, events, values):
        self._library = library
        self._reference = reference
        self._in_collection = in_collection
        self._values = values
        self._events = events

        try:
            self._regex = re.compile(self._reference)
        except Exception as e:
            logger.error(
                "Couldn't compile regex: " + str(self._reference) + "of mapping" + str(self) + ". Disabling it.")
            # Regex to never match anything
            self._regex = re.compile('a^')

    def is_applicable(self, reference):
        if self._reference == reference:
            return True
        return self._regex.match(reference)

    def applicable_filter(self, ctx):
        """
        Create a filter to check if the mapping is applicable
        :param ctx:
        :param mapping:
        :return:
        """

        def mapping_applicable_filter(name):
            if hasattr(ctx, name):
                try:
                    return self.is_applicable(getattr(ctx, name).__name__)
                except RecursionError as rerr:
                    logger.error("Recursion error on '" + str(
                        ctx) + "'. This might be because __get_attr__ is being wrapped. " + str(rerr))
            else:
                logger.warning("Can't access attribute '" + str(name) + "' on '" + str(ctx) + "'. Skipping.")
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
        return self._reference

    @property
    def library(self):
        return self._library

    def __str__(self):
        return "Mapping[" + str(self.reference) + ", lib=" + str(self.library) + "]"

    def __eq__(self, other):
        return self.reference == other.reference


class MappingCollection:
    def __init__(self, key, version, lib, lib_version, packages, mappings: List[PadsMapping]):
        self._mappings = mappings
        self._name = key
        self._version = version
        self._lib = lib
        self._lib_version = lib_version
        self._packages = packages

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

    @property
    def packages(self):
        return self._packages


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
                         schema.metadata["library"]["version"], list(yml["mappings"].keys()),
                         self._build_mappings(yml["mappings"], schema, True))

    def _build_mappings(self, node, schema: MappingSchema, entry):
        _fragments = []
        _children = []
        _events = set()
        _values = {}
        mappings = []

        # replace fragments
        for k, v in node.items():
            if entry:
                _children.append((k, v))
            elif k.startswith("::"):
                _fragments.append(k[2:])
            elif k.startswith("."):
                _children.append((k, v))
            elif k == "events":
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
            mappings = mappings + self._build_mappings(node, schema, False)
        else:
            if len(_children) > 0:
                for c, v in _children:
                    mappings = mappings + self._build_mappings(v, MappingSchema(schema.fragments, schema.metadata,
                                                                                reference=schema.reference + c,
                                                                                events=schema.events,
                                                                                values=schema.values), False)
            else:
                mappings.append(
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
        self.found_classes = {}

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
        if mapping.reference not in self.found_classes:
            self.found_classes[mapping.reference] = mapping

    def iter_found_mappings(self):
        for i, mapping in self.found_classes.items():
            yield mapping

    def get_libraries(self):
        all_libs = set()
        for key, mapping in self._mappings.items():
            all_libs.add(mapping.lib)
        return all_libs

    def get_relevant_mappings(self, module):
        """
        Function to find all relevant mappings. This produces a generator getting extended with found subclasses
        :return:
        """
        return chain(self.get_static_mappings(module), self.iter_found_mappings())

    def get_static_mappings(self, module):
        """
        Get all mappings defined in all mapping files.
        :return:
        """
        for collection in self._get_relevant_collections(module):
            for m in collection.mappings:
                yield m

    def _get_relevant_collections(self, module):
        for key, collection in self._mappings.items():
            if module.__name__ in collection.packages:
                yield collection
