import glob
import json
import os
from itertools import chain
from logging import warning
from os.path import expanduser
from typing import List

mapping_files = glob.glob(expanduser("~") + ".pypads/bindings/**.json")
mapping_files.extend(
    glob.glob(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/bindings/resources/mapping/**.json"))

# TODO only load mappings for installed libraries, check for versions and choose the best fitting one etc.
mappings = {}
for m in mapping_files:
    with open(m) as json_file:
        name = os.path.basename(json_file.name)
        mappings[name] = json.load(json_file)


class Hook:
    """
    This class defines a pypads hook. Hooks are injected into function calls to inject different functionality.
    """

    type = "always"

    def __init__(self, event):
        self._event = event

    @property
    def event(self):
        """
        Event to trigger on hook execution
        :return:
        """
        return self._event

    @classmethod
    def has_type_name(cls, type):
        return cls.type == type

    def is_applicable(self, *args, **kwargs):
        return True


class QualNameHook(Hook):
    """
    This class defines a pypads hook. Hooks are injected into function calls to inject different functionality.
    """

    type = "qual_name"

    def __init__(self, event, name):
        super().__init__(event)
        self._name = name

    @property
    def name(self):
        """
        Function name to hook to
        :return:
        """
        return self._name

    def is_applicable(self, *args, fn=None, **kwargs):
        return fn is not None and fn.__name__ == self.name


class PackageNameHook(Hook):
    """
    This class defines a pypads hook. Hooks are injected into function calls to inject different functionality.
    """

    type = "package_name"

    def __init__(self, event, name):
        super().__init__(event)
        self._name = name

    @property
    def name(self):
        """
        Package name to hook to
        :return:
        """
        return self._name

    def is_applicable(self, *args, mapping=None, **kwargs):
        return mapping is not None and self.name in mapping.reference


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
        if not isinstance(value, List):
            self._hooks = get_hooks(value)
        else:
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
                        hooks = get_hooks(alg["hooks"])

                    if alg["implementation"] and len(alg["implementation"]) > 0:
                        for library, reference in alg["implementation"].items():
                            yield Mapping(reference, library, alg, file, hooks)


def get_hooks(hook_map):
    hooks = []
    for event, hook_serialization in hook_map.items():
        if Hook.has_type_name(hook_serialization):
            hooks.append(Hook(event))
        else:
            for hook in hook_serialization:
                if isinstance(hook, Hook):
                    hooks.append(hook)
                elif hasattr(hook, 'type'):
                    if QualNameHook.has_type_name(hook['type']):
                        hooks.append(QualNameHook(event, hook['name']))

                    elif PackageNameHook.has_type_name(hook['type']):
                        hooks.append(PackageNameHook(event, hook['name']))
                    else:
                        warning("Type " + str(hook['type']) + " of hook " + str(hook) + " unknown.")
                else:
                    hooks.append(QualNameHook(event, hook))
    return hooks


def get_default_module_hooks(mapping):
    content = mappings[mapping.file]
    if "default_hooks" in content:
        if "modules" in content["default_hooks"]:
            if "fns" in content["default_hooks"]["modules"]:
                return get_hooks(content["default_hooks"]["modules"]["fns"])


def get_default_class_hooks(mapping):
    content = mappings[mapping.file]
    if "default_hooks" in content:
        if "classes" in content["default_hooks"]:
            if "fns" in content["default_hooks"]["classes"]:
                return get_hooks(content["default_hooks"]["classes"]["fns"])


def get_default_fn_hooks(mapping):
    content = mappings[mapping.file]
    if "default_hooks" in content:
        if "fns" in content["default_hooks"]:
            return get_hooks(content["default_hooks"]["fns"])


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
