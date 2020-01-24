import ast
import glob
import importlib
import inspect
import json
import operator
import os
import sys
import types
from importlib._bootstrap_external import PathFinder, SourceFileLoader
from inspect import isclass
from itertools import chain
from logging import warning, info, debug
from os.path import expanduser
from types import ModuleType
from typing import Callable

import mlflow
from boltons.funcutils import wraps

punched_modules = set()
punched_classes = set()
wrapped_classes = []
mapping_files = glob.glob(expanduser("~") + ".pypads/bindings/**.json")
mapping_files.extend(
    glob.glob(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/bindings/resources/mapping/**.json"))

mappings = {}
for mapping in mapping_files:
    with open(mapping) as json_file:
        name = os.path.basename(json_file.name)
        mappings[name] = json.load(json_file)


def get_implementations():
    for file, content in mappings.items():
        from pypads.base import get_current_pads
        if not get_current_pads().filter_mapping_files or file in get_current_pads():
            if "algorithms" in content:
                for alg in content["algorithms"]:
                    if alg["implementation"] and len(alg["implementation"]) > 0:
                        for library, package in alg["implementation"].items():
                            yield package, library, alg, content, file


sub_classes = []


def get_sub_classes():
    for (package, library, alg, content, file) in sub_classes:
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

        punched_modules.add(module.__name__)

        for name in dir(module):
            reference = getattr(module, name)
            if hasattr(reference, "mro"):
                try:
                    overlap = set(reference.mro()) & punched_classes
                    if bool(overlap):
                        # TODO maybe only for the first one
                        for o in overlap:
                            sub_classes.append((reference.__module__ + "." + reference.__qualname__, o.pypads_library,
                                                o.pypads_alg, o.pypads_content, o.pypads_file))
                except Exception as e:
                    debug("Skipping superclasses of " + str(reference))

        for package, library, alg, content, file in chain(get_implementations(), get_sub_classes()):
            if package.rsplit('.', 1)[0] == module.__name__:
                reference_name = package.rsplit('.', 1)[-1]
                if hasattr(module, reference_name):
                    setattr(module, reference_name, _wrap(getattr(module, reference_name), package, library, alg,
                                                          content, file))
                else:
                    warning(str(reference_name) + " not found on " + str(
                        module) + ". Your mapping might not be compatible with the used version of the library.")

        return out


class PyPadsFinder(PathFinder):
    """
    Import lib extension. This finder provides a special loader if mapping files contain the object.
    """

    def find_spec(cls, fullname, path=None, target=None):
        try:
            # Search and skip if not found
            next(i for i, _, _, _, _ in chain(get_sub_classes(), get_implementations()) if
                 i.rsplit('.', 1)[0] == fullname)
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


def new_method_proxy(func):
    """
    Proxy method for calling the non-punched function.
    :param func:
    :return:
    """

    def inner(self, *args):
        return func(self._pads_wrapped_instance, *args)

    return inner


def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])


def _wrap(wrappee, package, library, alg, content, file):
    """
    Wrapping function for duck punching all objects.
    :param wrappee: object to wrap
    :param package: package of the object to wrap
    :param content: related mapping in the mapping file
    :param file: mapping file
    :return: duck punched / wrapped object
    """
    debug("Wrapping: " + str(wrappee))
    if isclass(wrappee):

        # TODO what about classes deriving from other slots?
        for clazz in all_subclasses(wrappee):
            # duck_punch all subclasses if not already defined in implementations
            # todo visitors on estimators which have subclasses
            sub_classes.append((clazz.__module__ + "." + clazz.__qualname__, library, alg, content, file))

        # Already tracked base_classes should be skipped and we link directly to the wrapped class
        stop = False
        while not stop:
            try:
                wrappee = wrappee.pypads_wrappee
            except AttributeError:
                stop = True

        # TODO does this work with slot wrappers?
        if hasattr(wrappee.__init__, "__module__"):
            class ClassWrapper(wrappee):

                pypads_wrappee = wrappee
                pypads_package = package
                pypads_library = library
                pypads_alg = alg
                pypads_content = content
                pypads_file = file

                @wraps(wrappee.__init__)
                def __init__(self, *args, **kwargs):
                    print("Pypads tracked class " + str(wrappee) + " initialized.")
                    wrappee_instance = wrappee(*args, **kwargs)
                    self.__dict__ = wrappee_instance.__dict__
                    self._pads_wrapped_instance = wrappee_instance

                def __getattribute__(self, item):
                    # print("__getattribute__ on class of " + str(wrappee) + " with name " + item)
                    # if we try to get the wrapped instance give it
                    if item == "_pads_wrapped_instance":
                        return object.__getattribute__(self, item)

                    orig_attr = getattr(self._pads_wrapped_instance, item)

                    if callable(orig_attr):

                        pypads_fn = [k for k, v in content["hook_fns"].items() if item in v]

                        from pypads.base import get_current_pads
                        pads = get_current_pads()

                        # Get logging config
                        run = pads.mlf.get_run(mlflow.active_run().info.run_id)

                        fn_stack = [orig_attr]

                        from pypads.base import CONFIG_NAME
                        if CONFIG_NAME in run.data.tags:
                            config = ast.literal_eval(run.data.tags[CONFIG_NAME])
                            for log_event, event_config in config["events"].items():

                                hook_fns = event_config["on"]
                                if "with" in event_config:
                                    hook_params = event_config["with"]
                                else:
                                    hook_params = {}

                                # If one hook_fns is in this config.
                                if set(hook_fns) & set(pypads_fn):

                                    fn = pads.function_registry.find_function(log_event)
                                    if fn:
                                        hooked = types.MethodType(fn, self)

                                        @wraps(orig_attr)
                                        def ctx_setter(self, *args, pypads_hooked_fn=hooked,
                                                       pypads_hook_params=hook_params, **kwargs):

                                            # check for name collision
                                            if set([k for k, v in kwargs.items()]) & set(
                                                    [k for k, v in pypads_hook_params.items()]):
                                                warning("Hook parameter is overwriting a parameter in the standard "
                                                        "model call. This most likely will produce side effects.")

                                            return pypads_hooked_fn(pypads_wrappe=wrappee, pypads_package=package,
                                                                    pypads_item=item, pypads_fn_stack=fn_stack, *args,
                                                                    **{**kwargs, **pypads_hook_params})

                                        # Overwrite fn call structure
                                        fn_stack.append(types.MethodType(ctx_setter, self))
                        return fn_stack.pop()
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
            debug("Success wrapping: " + str(wrappee))
            punched_classes.add(wrappee)
            punched_classes.add(out)
        else:
            debug("Can't wrap constructor. Skipping for now subclasses have to be duck punched.")
            out = wrappee
            try:
                setattr(wrappee, "pypads_package", package)
                setattr(wrappee, "pypads_library", library)
                setattr(wrappee, "pypads_alg", alg)
                setattr(wrappee, "pypads_content", content)
                setattr(wrappee, "pypads_file", file)
                punched_classes.add(wrappee)
                punched_classes.add(out)
            except TypeError as e:
                debug("Can't modify class for pypads references: " + str(e))
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
    """
    Function to add the custom import logic to the python importlib execution
    :return:
    """
    sys.meta_path.insert(0, PyPadsFinder())


def activate_tracking(mod_globals=None):
    """
    Function to duck punch all objects defined in the mapping files. This should at best be called before importing
    any libraries.
    :param mod_globals: globals() object used to duckpunch already loaded classes
    :return:
    """
    extend_import_module()
    for i in set(i.rsplit('.', 1)[0] for i, _, _, _, _ in get_implementations() if
                 i.rsplit('.', 1)[0] in sys.modules and i.rsplit('.', 1)[0] not in punched_modules):
        spec = importlib.util.find_spec(i)
        loader = PyPadsLoader(spec.name, spec.origin)
        module = loader.load_module(i)
        loader.exec_module(module)
        sys.modules[i] = module
        warning(i + " was imported before PyPads. PyPads has to be imported before importing tracked libraries."
                    " Otherwise it can only try to wrap classes on global level.")
        if mod_globals:
            for k, l in mod_globals.items():
                if isinstance(l, ModuleType) and i in str(l):
                    mod_globals[k] = module
                elif inspect.isclass(l) and i in str(l) and hasattr(module, l.__name__):
                    if k not in mod_globals:
                        warning(i + " was imported before PyPads, but couldn't be modified on globals.")
                    else:
                        info("Modded " + i + " after importing it. This might fail.")
                        mod_globals[k] = getattr(module, l.__name__)
