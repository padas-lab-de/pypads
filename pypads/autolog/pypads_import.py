import ast
import glob
import importlib
import inspect
import json
import operator
import os
import pickle
import sys
import types
from importlib._bootstrap_external import PathFinder, SourceFileLoader
from inspect import isclass
from logging import warning, info
from os.path import expanduser
from pickle import PicklingError
from types import ModuleType
from typing import Callable

import mlflow
from boltons.funcutils import wraps
from mlflow.utils.autologging_utils import try_mlflow_log

punched_modules = []
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
        impls = [(package, content, file) for package, _, _, content, file in get_implementations() if
                 package.rsplit('.', 1)[0] == module.__name__]
        for package, content, file in impls:
            setattr(module, package.rsplit('.', 1)[-1], _wrap(getattr(module, package.rsplit('.', 1)[-1]), package,
                                                              content, file))
        # sys.modules.update({fullname: _wrap(module)})

        return out


class PyPadsFinder(PathFinder):
    """
    Import lib extension. This finder provides a special loader if mapping files contain the object.
    """

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


def new_method_proxy(func):
    """
    Proxy method for calling the non-punched function.
    :param func:
    :return:
    """
    def inner(self, *args):
        return func(self._pads_wrapped_instance, *args)

    return inner


def _wrap(wrappee, package, mapping, m_file):
    """
    Wrapping function for duck punching all objects.
    :param wrappee: object to wrap
    :param package: package of the object to wrap
    :param mapping: related mapping in the mapping file
    :param m_file: mapping file
    :return: duck punched / wrapped object
    """
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

                        pypads_fn = [k for k, v in mapping["hook_fns"].items() if item in v]

                        from pypads.base import get_current_pads
                        pads = get_current_pads()

                        # Get logging config
                        run = pads.mlf.get_run(mlflow.active_run().info.run_id)

                        fn_stack = [orig_attr]

                        from pypads.base import CONFIG_NAME
                        if CONFIG_NAME in run.data.tags:
                            config = ast.literal_eval(run.data.tags[CONFIG_NAME])
                            for log_event, hook_fns in config["events"].items():

                                # If one hook_fns is in this config.
                                if set(hook_fns) & set(pypads_fn):

                                    fn = pads.function_registry.find_function(log_event)
                                    if fn:
                                        hooked = types.MethodType(fn, self)

                                        @wraps(orig_attr)
                                        def ctx_setter(self, *args, pypads_hooked_fn=hooked, **kwargs):
                                            return pypads_hooked_fn(pypads_wrappe=wrappee, pypads_package=package,
                                                                    pypads_item=item, pypads_fn_stack=fn_stack, *args,
                                                                    **kwargs)

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
        else:
            out = wrappee
    elif isinstance(wrappee, Callable):
        class FunctionWrapper:

            def __init__(self,):
                self.__code__ = wrappee.__code__
                self.__globals__ = wrappee.__globals__
                self._pads_wrapped_instance = None

            @wraps(wrappee)
            def __call__(self, *args, **kwargs):
                print("Pypads wrapped function " + str(wrappee) + "created.")
                pypads_fn = [k for k, v in mapping["hook_fns"].items() if wrappee.__name__ in v]

                from pypads.base import get_current_pads
                pads = get_current_pads()

                # Get logging config
                run = pads.mlf.get_run(mlflow.active_run().info.run_id)
                fn_stack = [wrappee]
                from pypads.base import CONFIG_NAME
                if CONFIG_NAME in run.data.tags:
                    config = ast.literal_eval(run.data.tags[CONFIG_NAME])
                    for log_event, hook_fns in config["events"].items():
                        if set(hook_fns) & set(pypads_fn):
                            fn = pads.function_registry.find_function(log_event)
                            if fn:
                                # hooked = types.FunctionType(fn.__code__, globals())

                                def ctx_setter(*args, pypads_hooked_fn=fn, **kwargs):
                                    return pypads_hooked_fn(self,pypads_wrappe=wrappee, pypads_package=package,
                                                            pypads_item=wrappee.__name__, pypads_fn_stack=fn_stack,
                                                            *args,
                                                            **kwargs)

                                fn_stack.append(ctx_setter)
                while fn_stack:
                    out = fn_stack.pop()(*args, **kwargs)
                print("Output: " + str(out))
                return out

        out = FunctionWrapper()
    else:
        # print("Wrapped variable " + str(wrappee))
        out = wrappee
    return out


def to_folder(ctx):
    """
    TODO
    :param ctx:
    :return:
    """
    return os.path.join(expanduser("~") + "/.pypads/" + mlflow.active_run().info.experiment_id + "/" + ctx)


def try_write_artifact(file_name, obj):
    """
    Function to write an artifact to disk. TODO
    :param file_name:
    :param obj:
    :return:
    """
    path = to_folder(file_name)

    # Todo allow for configuring output format
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    try:
        with open(path, "wb+") as fd:
            pickle.dump(obj, fd)
    except PicklingError as e:
        warning("Couldn't pickle output. Trying to save toString instead. " + str(e))
        with open(path, "w+") as fd:
            fd.write(str(obj))

    try_mlflow_log(mlflow.log_artifact, path)


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
        warning(i + " was imported before PyPads. PyPads has to imported before importing tracked libraries."
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
