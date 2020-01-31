import glob
import json
import os
from itertools import chain
from os.path import expanduser

mapping_files = glob.glob(expanduser("~") + ".pypads/bindings/**.json")
mapping_files.extend(
    glob.glob(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/bindings/resources/mapping/**.json"))

# TODO only load mappings for installed libraries, check for versions and choose the best fitting one etc.
mappings = {}
for m in mapping_files:
    with open(m) as json_file:
        name = os.path.basename(json_file.name)
        mappings[name] = json.load(json_file)


class Mapping:
    """
    Mapping for an algorithm defined by a pypads mapping file
    """

    def __init__(self, reference, library, algorithm, file, hooks):
        self._hooks = hooks
        self._algorithm = algorithm
        self._library = library
        self._reference = reference
        self._file = file

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
        self._hooks = value


def get_implementations():
    """
    Get all mappings defined in all mapping files.
    :return:
    """
    for file, content in mappings.items():
        from pypads.base import get_current_pads
        if not get_current_pads().filter_mapping_files or file in get_current_pads():
            if "algorithms" in content:
                for alg in content["algorithms"]:
                    hooks = None
                    if "hooks" in alg:
                        hooks = alg["hooks"]
                    if alg["implementation"] and len(alg["implementation"]) > 0:
                        for library, reference in alg["implementation"].items():
                            yield Mapping(reference, library, alg, file, hooks)


found_classes = {}
found_fns = {}


def iter_found_classes():
    for i, mapping in found_classes.items():
        yield mapping


def iter_found_fns():
    for i, mapping in found_fns.items():
        yield mapping


def get_relevant_mappings():
    """
    Function to find all relevant mappings. This produces a generator getting extended with found subclasses
    :return:
    """
    return chain(get_implementations(), iter_found_classes(), iter_found_fns())
