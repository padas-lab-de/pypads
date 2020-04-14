import glob
import json
import os
from itertools import chain
from os.path import expanduser
from typing import List

from pypads import logger
from pypads.autolog.hook import get_hooks

mapping_files = glob.glob(expanduser("~") + ".pypads/bindings/**.json")
mapping_files.extend(
    glob.glob(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/bindings/resources/mapping/**.json"))


class AlgorithmMeta:
    def __init__(self, name, concepts):
        self._concepts = concepts
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def concepts(self):
        return self._concepts

    def __eq__(self, other):
        return self.name == other.name


class AlgorithmMapping:
    """
    Mapping for an algorithm defined by a pypads mapping file
    """

    def __init__(self, reference, library, algorithm: AlgorithmMeta, file, hooks):
        self._hooks = hooks
        self._algorithm = algorithm
        self._library = library
        self._reference = reference
        self._file = file
        self._in_collection = None

    @property
    def in_collection(self):
        return self._in_collection

    @in_collection.setter
    def in_collection(self, value):
        self._in_collection = value

    @property
    def file(self):
        return self._file

    @property
    def reference(self):
        return self._reference

    @property
    def library(self):
        return self._library

    @property
    def algorithm(self):
        return self._algorithm

    @property
    def hooks(self):
        return self._hooks

    @hooks.setter
    def hooks(self, value):
        if not isinstance(value, List):
            self._hooks = get_hooks(value)
        else:
            self._hooks = value

    def __str__(self):
        return "Mapping[" + str(self.file) + ":" + str(self.reference) + ", lib=" + str(self.library) + ", alg=" + str(
            self.algorithm) + ", hooks=" + str(self.hooks) + "]"

    def __eq__(self, other):
        # TODO also check for reference, file,, in_collection?
        if self.hooks and other.hooks:
            return set(self.hooks) == set(
                other.hooks) and self.algorithm == other.algorithm and self.library == other.library
        elif not self.hooks and not other.hooks:
            return self.algorithm == other.algorithm and self.library == other.library
        else:
            return False


class MappingCollection:
    def __init__(self, key, default_hooks, algorithms: List[AlgorithmMapping]):
        self._default_hooks = default_hooks
        self._algorithms = algorithms
        self._key = key

    @property
    def key(self):
        return self._key

    @property
    def default_hooks(self):
        return self._default_hooks

    @property
    def algorithms(self):
        for alg in self._algorithms:
            hooks = None
            if "hooks" in alg:
                hooks = get_hooks(alg["hooks"])

            if alg["implementation"] and len(alg["implementation"]) > 0:
                for library, reference in alg["implementation"].items():
                    mapping = AlgorithmMapping(reference, library, AlgorithmMeta(alg, []), self.key, hooks)
                    mapping.in_collection = self
                    yield mapping

    def get_default_module_hooks(self):
        if "modules" in self._default_hooks:
            if "fns" in self._default_hooks["modules"]:
                return get_hooks(self._default_hooks["modules"]["fns"])

    def get_default_class_hooks(self):
        if "classes" in self._default_hooks:
            if "fns" in self._default_hooks["classes"]:
                return get_hooks(self._default_hooks["classes"]["fns"])

    def get_default_fn_hooks(self):
        if "fns" in self._default_hooks:
            return get_hooks(self._default_hooks["fns"])


class MappingFile(MappingCollection):

    def __init__(self, name, json):
        super().__init__(name, json['default_hooks'] if 'default_hooks' in json else {
            "modules": {
                "fns": {}
            },
            "classes": {
                "fns": {}
            },
            "fns": {}
        }, json["algorithms"] if 'algorithms' in json else [])
        self._lib = json['metadata']['library']
        self._lib_version = json['metadata']['library_version']
        self._version = json['metadata']['mapping_version']
        self._name = name

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
        if isinstance(mapping, MappingFile):
            key = mapping.lib

        if key is None:
            logger.error(
                "Couldn't add mapping " + str(mapping) + " to the pypads mapping registry. Lib or key are undefined.")
        else:
            self._mappings[key] = mapping

    def load_mapping(self, path):
        with open(path) as json_file:
            name = os.path.basename(json_file.name)
            logger.info("Added mapping file with name: " + str(name))
            content = json.load(json_file)
            self.add_mapping(MappingFile(name, json=content))

    def add_found_class(self, mapping):
        if mapping.reference not in self.found_classes:
            self.found_classes[mapping.reference] = mapping

    def iter_found_classes(self):
        for i, mapping in self.found_classes.items():
            yield mapping

    def get_libraries(self):
        all_libs = set()
        for key, mapping in self._mappings.items():
            all_libs.add(mapping.lib)
        return all_libs

    def get_relevant_mappings(self):
        """
        Function to find all relevant mappings. This produces a generator getting extended with found subclasses
        :return:
        """
        return chain(self.get_algorithms(), self.iter_found_classes())

    def get_algorithms(self):
        """
        Get all mappings defined in all mapping files.
        :return:
        """

        for key, mapping in self._mappings.items():
            for alg in mapping.algorithms:
                yield alg
