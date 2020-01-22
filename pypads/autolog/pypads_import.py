import glob
import importlib
import inspect
import json
import operator
import os
import pickle
import random
import sys
import types
from importlib._bootstrap_external import PathFinder, SourceFileLoader
from importlib.resources import read_text
from inspect import isclass
from logging import warning
from os.path import expanduser
from types import ModuleType
from typing import Callable

import mlflow
from boltons.funcutils import wraps

from pypads import _name
from pypads.bindings.generic_visitor import default_visitor

punched_modules = []
mapping_files = glob.glob(expanduser("~") + ".pypads/bindings/**.json")
mapping_files.extend(glob.glob(os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..')) + "/bindings/resources/mapping/**.json"))

mappings = {}
for mapping in mapping_files:
    with open(mapping) as json_file:
        name = os.path.basename(json_file.name)
        mappings[name] = json.load(json_file)


def get_implementations():
    for file, content in mappings.items():
        for alg in content["algorithms"]:
            if alg["implementation"] and len(alg["implementation"]) > 0:
                for library, package in alg["implementation"].items():
                    yield package, library, alg, content, file


class PyPadsLoader(SourceFileLoader):

    def load_module(self, fullname):
        module = super().load_module(fullname)
        return module

    def create_module(self, spec):
        module = super().create_module(spec)
        return module

    def exec_module(self, module):
        out = super().exec_module(module)

        punched_modules.append(module.__name__)
        impls = [(package, content, file) for package, _, _, content, file in get_implementations() if package.rsplit('.', 1)[0] == module.__name__]
        for package, content, file in impls:
            setattr(module, package.rsplit('.', 1)[-1], _wrap(getattr(module, package.rsplit('.', 1)[-1]), package,
                                                              content, file))
        # sys.modules.update({fullname: _wrap(module)})

        return out


class PyPadsFinder(PathFinder):

    def find_spec(cls, fullname, path=None, target=None):
        try:
            # Search and skip if not found (kinda like a loop)
            next(i for i, _, _, _, _ in get_implementations() if i.rsplit('.', 1)[0] == fullname)
            if fullname not in sys.modules:
                path_ = sys.meta_path[1:]
                i = iter(path_)
                spec = None
                try:
                    while not spec:
                        importer = next(i)
                        if hasattr(importer, "find_spec"):
                            spec = importer.find_spec(fullname, path)
                except StopIteration:
                    pass
                if spec:
                    spec.loader = PyPadsLoader(fullname, spec.loader.path)
                    return spec

        except StopIteration:
            pass


def _wrapped_name(path):
    return "pypads_" + path


def new_method_proxy(func):
    def inner(self, *args):
        return func(self._pads_wrapped_instance, *args)

    return inner


def _wrap(wrappee, package, mapping, m_file):
    # print("Wrapping: " + str(wrappee))

    if isclass(wrappee):

        # TODO what about classes deriving directly from object or other slots?
        if "slot wrapper" not in str(wrappee.__init__):
            class ClassWrapper(wrappee):

                @wraps(wrappee.__init__)
                def __init__(self, *args, **kwargs):
                    print("Pypads tracked class " + str(wrappee) + " initialized.")
                    wrappee_instance = wrappee(*args, **kwargs)
                    ClassWrapper._pads_wrapped_instance = wrappee_instance
                    self.__dict__ = wrappee_instance.__dict__

                def __getattribute__(self, item):
                    # print("__getattribute__ on class of " + str(wrappee) + " with name " + item)
                    if item == "_pads_wrapped_instance":
                        return object.__getattribute__(self, item)
                    orig_attr = getattr(self._pads_wrapped_instance, item)
                    if callable(orig_attr):

                        pypads_fn = [k for k, v in mapping["fns"].items() if item in v]
                        events = [k for k, v in mapping["events"].items() if item in v or set(pypads_fn) & set(v)]

                        if "parameters" in events:
                            @wraps(orig_attr)
                            def hooked(self, *args, **kwargs):
                                result = orig_attr(*args, **kwargs)
                                # prevent wrapped_class from becoming unwrapped
                                visitor = default_visitor(self)

                                for k, v in visitor[0]["steps"][0]["hyper_parameters"]["model_parameters"].items():
                                    mlflow.log_param(package + "." + k, v)
                                if result is self._pads_wrapped_instance:
                                    return self
                                return result
                            orig_attr = hooked

                        if "output" in events:
                            @wraps(orig_attr)
                            def hooked(self, *args, **kwargs):
                                result = orig_attr(*args, **kwargs)
                                name = wrappee.__name__ + "." + item + "_output.bin"
                                path = os.path.join(expanduser("~") + "/.pypads/test/" + name)
                                fd = open(path, "w+")
                                pickle.dump(result, fd)
                                mlflow.log_artifact(path)
                                if result is self._pads_wrapped_instance:
                                    return self
                                return result
                            orig_attr = hooked

                        if "input" in events:
                            @wraps(orig_attr)
                            def hooked(self, *args, **kwargs):
                                name = wrappee.__name__ + "." + item + "_input.bin"
                                path = os.path.join(expanduser("~") + "/.pypads/test/" + name)
                                fd = open(path, "w+")
                                pickle.dump({"args": args, **kwargs}, fd)
                                mlflow.log_artifact(path)
                                result = orig_attr(*args, **kwargs)
                                if result is self._pads_wrapped_instance:
                                    return self
                                return result
                            orig_attr = hooked

                        return types.MethodType(orig_attr, self)
                    return orig_attr

                # Need to pretend to be the wrapped class, for the sake of objects that
                # care about this (especially in equality tests)
                # __class__ = property(new_method_proxy(operator.attrgetter("__class__")))
                __eq__ = new_method_proxy(operator.eq)
                __lt__ = new_method_proxy(operator.lt)
                __gt__ = new_method_proxy(operator.gt)
                __ne__ = new_method_proxy(operator.ne)
                __hash__ = new_method_proxy(hash)

                # List/Tuple/Dictionary methods support
                __getitem__ = new_method_proxy(operator.getitem)
                __setitem__ = new_method_proxy(operator.setitem)
                __delitem__ = new_method_proxy(operator.delitem)
                __iter__ = new_method_proxy(iter)
                __len__ = new_method_proxy(len)
                __contains__ = new_method_proxy(operator.contains)
                __instancecheck__ = new_method_proxy(operator.attrgetter("__instancecheck__"))

            out = ClassWrapper
        else:
            out = wrappee
    elif isinstance(wrappee, Callable):
        def wrapper(*args, **kwargs):
            # print("Wrapped function " + str(wrappee))
            out = wrappee(*args, **kwargs)
            # print("Output: " + str(out))
            return out

        out = wrapper
    else:
        # print("Wrapped variable " + str(wrappee))
        out = wrappee
    return out


def extend_import_module():
    sys.meta_path.insert(0, PyPadsFinder())


def pypads_track(mod_globals=None):
    extend_import_module()
    for i in set(i.rsplit('.', 1)[0] for i, _, _, _, _ in get_implementations() if
                 i.rsplit('.', 1)[0] in sys.modules and i.rsplit('.', 1)[0] not in punched_modules):
        spec = importlib.util.find_spec(i)
        loader = PyPadsLoader(spec.name, spec.origin)
        module = loader.load_module(i)
        loader.exec_module(module)
        sys.modules[i] = module
        if mod_globals:
            for k, l in mod_globals.items():
                if isinstance(l, ModuleType) and i in str(l):
                    mod_globals[k] = module
                elif inspect.isclass(l) and i in str(l) and hasattr(module, l.__name__):
                    if k not in mod_globals:
                        warning(i + " was imported before pypads, but couldn't be modified on globals.")
                    else:
                        mod_globals[k] = getattr(module, l.__name__)
        else:
            warning(i + " was imported before pypads. Pypads has to imported before importing tracked libraries."
                " Otherwise it only can wrap classes on global level.")

    mlflow.set_tracking_uri(uri="file:/Users/weissger/.mlruns")
    mlflow.start_run()
    mlflow.set_tag("pypads", "pypads")
