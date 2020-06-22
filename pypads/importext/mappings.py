import glob
import os
import re
from typing import List, Set, Tuple, Generator, Iterable

import pkg_resources
import yaml

from pypads import logger
from pypads.bindings.anchors import Anchor, get_anchor
from pypads.bindings.hooks import Hook
from pypads.importext.package_path import RegexMatcher, PackagePath, PackagePathMatcher, \
    SerializableMatcher, Package
from pypads.importext.semver import parse_constraint

default_mapping_file_paths = []
default_mapping_file_paths.extend(glob.glob(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "bindings", "resources", "mapping", "**.yml"))))


class LibSelector:
    """
    Selector class holding version constraint and name of a library. @see poetry sem versioning
    """

    def __init__(self, name, version: str, specificity=None):
        super().__init__()
        self._name = name
        self._constraint = parse_constraint(version)
        self._specificity = specificity or self._calc_specificity()

    @staticmethod
    def from_dict(library):
        if library is None:
            return None
        return LibSelector(library["name"], library["version"])

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._constraint

    def _calc_specificity(self):
        """
        Calculates a value how specific the selector is. The more specific it is the higher the value is.
        TODO do some magic here
        :return:
        """
        return 0

    @property
    def specificity(self):
        """
        Returns a value how specific the selector is.
        :return:
        """
        return self._specificity

    def allows_any(self, other):  # type: (LibSelector) -> bool
        """
        Check if the constraint overlaps with another constaint.
        :param other:
        :return:
        """
        return re.compile(self._name).match(other.name) and self._constraint.allows_any(other.version)

    def allows(self, name, version):  # type: (str, "Version") -> bool
        """
        Check if the constraint allows given version number.
        :param name:
        :param version:
        :return:
        """
        from pypads.importext.semver import Version
        return re.compile(self._name).match(name) and self._constraint.allows(Version.parse(version))


class Mapping:
    """
    Mapping for an algorithm defined by a pypads mapping file
    """

    def __init__(self, matcher: PackagePathMatcher, in_collection, anchors, values):
        self._in_collection = in_collection
        self._values = values
        self._hooks = set()
        from pypads.bindings.hooks import Hook
        for a in anchors:
            self._hooks.add(Hook(a, self))
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
    def in_collection(self):  # type: () -> MappingCollection
        return self._in_collection

    @in_collection.setter
    def in_collection(self, value):
        self._in_collection = value

    @property
    def reference(self):
        return self._matcher.serialize()

    @property
    def library(self) -> LibSelector:
        return self.in_collection.lib

    @property
    def hooks(self):  # type: () -> Set[Hook]
        return self._hooks

    @property
    def values(self):
        return self._values

    @property
    def matcher(self):
        return self._matcher

    def __str__(self):
        return "Mapping[" + str(self.reference) + ", lib=" + str(self.library) + ", hooks=" + str(self.hooks) + "]"

    def __eq__(self, other):
        return self.reference == other.reference and self.hooks == other.hooks and self.values == other.values

    def __hash__(self):
        return hash((self.reference, "|".join([str(h) for h in self.hooks]), str(self.values)))


class MappingCollection:
    def __init__(self, key, version, library):
        """
        Object holding a set of mappings related to a library
        :param key: Name / key of the collection
        :param version: Version of the collection
        :param library: Library information including library version constraint and name
        """
        self._mappings = {}
        self._name = key
        self._version = version
        self._lib = LibSelector.from_dict(library)

    @property
    def version(self):
        return self._version

    @property
    def lib(self):
        return self._lib

    @property
    def name(self):
        return self._name

    @property
    def mappings(self):
        return self._mappings

    def add_mapping(self, mapping: Mapping):
        """
        Add a mapping to the collection.
        :param mapping: Mapping to be added.
        :return:
        """
        path_map = self._mappings
        for segment in mapping.matcher.matchers:
            if segment not in path_map:
                path_map[segment] = dict()
            path_map = path_map[segment]
        if ":mapping" not in path_map:
            path_map[":mapping"] = []
        path_map[":mapping"].append(mapping)

    def _get_all_mappings(self, current_path=None):
        """
        Get all mappings stored behind place in the mapping dict.
        :param current_path: A reference to a sub dict in the mapping dict.
        :return: All mappings stored below the current path
        """
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
        """
        Find all mappings matching given segments. The segments foo.bar for example are matched by foo.bar.a
        and foo.bar.{re:.*} etc.
        :param segments: Segments to look for
        :param current_path: Place in the mapping dict from which we are looking in mapping dict. We iterate through
        the map to find relevant mapping files.
        :return:
        """
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


def make_run_time_mapping_collection(lib):
    return MappingCollection("_pypads_runtime", "0.0.0", {"name": lib, "version": "0.0.0"})


class MappingSchema:
    """
    Schema holding the context of a mapping. This is used to build mappings iteratively.
    """

    def __init__(self, fragments, metadata, matcher: PackagePathMatcher, anchors, values):
        self._fragments = fragments
        self._metadata = metadata
        self._matcher = matcher
        if not isinstance(anchors, Iterable):
            anchors = [anchors]
        self._anchors = set()
        for anchor in anchors:
            self._anchors.add(get_anchor(anchor) or Anchor(anchor, "Runtime anchor. No description available."))
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
    def anchors(self):
        return self._anchors

    def get(self, key):
        return self._values[key]

    def has(self, key):
        return key in self._values


class SerializedMapping(MappingCollection):
    """
    Mapping serialized by yaml.
    """

    def __init__(self, key, content):
        yml = yaml.load(content, Loader=yaml.SafeLoader)
        schema = MappingSchema(yml["fragments"] if "fragments" in yml else [], yml["metadata"], PackagePathMatcher(""),
                               set(), {})
        super().__init__(key, schema.metadata["version"], schema.metadata["library"])
        self._build_mappings(yml["mappings"], schema)

    def _build_mappings(self, node, schema: MappingSchema):
        """
        Build real mapping objects from a given yaml serialization.
        :param node: Yaml node holding the mappings
        :param schema: Current schema holding the context of the mapping. Initially this is an empty schema.
        :return: List of all mappings in the serialization
        """
        _fragments = []
        _children = []
        _anchors = set()
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
            elif k == "hooks":
                if isinstance(v, str):
                    _anchors.add(v)
                elif isinstance(v, List):
                    for anchor in v:
                        _anchors.add(anchor)
            elif k == "data":
                _values[k] = v

        for p in _fragments:
            for k, v in schema.fragments[p].items():
                node[k] = v
            del node[";" + p]

        schema = MappingSchema(schema.fragments, schema.metadata, matcher=schema.matcher,
                               anchors=_anchors.union(schema.anchors),
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
                                                                                    anchors=schema.anchors,
                                                                                    values=schema.values))}
            elif schema.matcher.matchers is not None:
                self.add_mapping(
                    Mapping(schema.matcher, self, schema.anchors, schema.values))
        return mappings


class MappingFile(SerializedMapping):
    """
    Class referencing a file holding a mapping.
    """

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

    def __init__(self, pypads, *paths):
        # default paths
        self._pypads = pypads
        mapping_file_paths = []
        if pypads.config["include_default_mappings"]:
            # Use our with the package delivered mapping files
            mapping_file_paths.extend(glob.glob(os.path.join(pypads.folder, "bindings", "**.yml")))
            mapping_file_paths.extend(default_mapping_file_paths)
        if paths:
            mapping_file_paths.extend(paths)

        self._mappings = {}

        for path in mapping_file_paths:
            self.load_mapping(path)

    @staticmethod
    def from_params(pypads, mapping_input):
        """
        Method to create a mapping registry from input parameters given to the pypads app.
        :param pypads: Pypads app
        :param mapping_input: Input parameters of form: Path as string, Mapping object or a list of these
        :return: Mapping registry
        """
        paths = []
        mappings = []

        # Allow for referencing mappings via a path or via a direct reference to the object
        if not isinstance(mapping_input, List):
            mapping_input = [mapping_input]
        for m in mapping_input:
            if isinstance(m, str):
                paths.append(m)
            if isinstance(m, MappingCollection):
                mappings.append(m)

        # Pass paths to the constructor and add mappings to the registry manually
        registry = MappingRegistry(pypads, *paths)
        for mapping in mappings:
            if mapping:
                if isinstance(mapping, dict):
                    for key, mapping in mapping.items():
                        registry.add_mapping(mapping, key=key)
                else:
                    registry.add_mapping(mapping, key=mapping.lib)
        return registry

    def get_entries(self):  # type: () -> Generator[Tuple[LibSelector, MappingCollection]]
        """
        Method returning all entries in the mapping registry in a typed manner.
        :return: Generator of item tuples
        """
        for s, c in self._mappings.items():
            yield s, c

    def add_mapping(self, mapping: MappingCollection, key=None):
        """
        Method to add a mapping to the registry.
        :param mapping: Mapping collection to be added to the registry.
        :param key: Key for the mapping collection. TODO remove key?
        :return:
        """
        if key is None and isinstance(mapping, MappingFile):
            key = mapping.lib

        if key is None:
            logger.error(
                "Couldn't add mapping " + str(mapping) + " to the pypads mapping registry. Lib or key are undefined.")
        else:
            self._mappings[key] = mapping

    def load_mapping(self, path):
        """
        Load and add mapping at given path.
        :param path: Path to the mapping file.
        :return:
        """
        self.add_mapping(MappingFile(path))

    def get_libraries(self):
        """
        Find all supported libraries in the mapping registry.
        :return:
        """
        all_libs = set()
        for key, mapping in self._mappings.items():
            all_libs.add(mapping.lib)
        return all_libs

    def get_relevant_mappings(self, package: Package):
        """
        Function to find all relevant mappings. This produces a generator getting extended with found subclasses
        :return:
        """
        if any([package.path.segments[0] == s.name for s, _ in self.get_entries()]):
            lib_version = None

            # TODO what about libraries where package name != pip name
            # Try to get version of installed package
            try:
                import sys
                base_package = sys.modules[str(package.path.segments[0])]
                if hasattr(base_package, "__version__"):
                    lib_version = getattr(base_package, "__version__")
                else:
                    lib_version = pkg_resources.get_distribution(str(package.path.segments[0])).version
            except Exception as e:
                logger.debug("Couldn't get version of package {}".format(package.path))

            mappings = set()

            # Take only mappings which are fitting for versions
            if lib_version:
                for k, collection in [(s, c) for s, c in self.get_entries() if
                                      s.allows(str(package.path.segments[0]), lib_version)]:
                    for m in collection.find_mappings(package.path.segments):
                        mappings.add(m)
            else:
                for k, collection in [(s, c) for s, c in self.get_entries() if s.name == package.path.segments[0]]:
                    for m in collection.find_mappings(package.path.segments):
                        mappings.add(m)
            return mappings
        return set()


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

    def __hash__(self):
        return self._mapping.__hash__()

    def __eq__(self, other):
        return self.mapping == other.mapping and self.package_path == other.package_path
