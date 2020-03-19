import ast
import atexit
import glob
import io
import os
import pickle
from contextlib import contextmanager
from functools import wraps
from logging import warning, debug
from os.path import expanduser
from types import FunctionType
from typing import List, Iterable

import mlflow
from ipywidgets import Output
from mlflow.tracking import MlflowClient

from pypads.autolog.hook import Hook
from pypads.autolog.mappings import AlgorithmMapping, MappingRegistry, AlgorithmMeta
from pypads.autolog.pypads_import import extend_import_module, duck_punch_loader
from pypads.autolog.wrapping.module_wrapping import punched_module_names
from pypads.caches import PypadsCache, Cache
from pypads.functions.analysis.call_tracker import CallTracker
from pypads.functions.analysis.validation.parameters import Parameter
from pypads.functions.loggers.data_flow import Input
from pypads.functions.loggers.debug import LogInit, Log
from pypads.functions.loggers.hardware import Disk, Ram, Cpu
from pypads.functions.loggers.metric import Metric
from pypads.functions.loggers.mlflow.mlflow_autolog import MlflowAutologger
from pypads.functions.loggers.pipeline_detection import PipelineTracker
from pypads.functions.run_init_loggers.hardware import ISystem, IRam, ICpu, IDisk, IPid
from pypads.logging_util import WriteFormats, try_write_artifact
from pypads.util import get_class_that_defined_method, is_package_available, dict_merge

current_pads = None
tracking_active = None


class FunctionRegistry:
    """
    This class holds function mappings. Logging functionalities get a name and a underlying function.
    Example.: parameters -> function logging the parameters of the library calls.
    {
    "parameters": <fn>,
    "model": <fn>
    }
    """

    def __init__(self, mapping=None):
        if mapping is None:
            mapping = {}
        self.fns = {}
        for key, value in mapping.items():
            if isinstance(value, Iterable):
                self._add_functions(key, value)
            elif callable(value):
                self._add_functions(key, {value})

    def find_functions(self, name, lib=None, version=None):
        if (name, lib, version) in self.fns:
            return self.fns[(name, lib, version)]
        elif (name, lib) in self.fns:
            return self.fns[(name, lib)]
        elif name in self.fns:
            return self.fns[name]
        else:
            pass
            # warning("Function call with name '" + name + "' is not linked with any logging functionality.")

    def add_functions(self, name, lib=None, version=None, *args: FunctionType):
        if lib:
            if version:
                key = (name, lib, version)
            else:
                key = (name, lib)
        else:
            key = name
        self._add_functions(key, args)

    def _add_functions(self, key, fns):
        if key not in self.fns:
            self.fns[key] = set()
        for fn in fns:
            self.fns[key].add(fn)


def _parameter_pickle(args, kwargs):
    with io.BytesIO() as file:
        pickle.dump((args, kwargs), file)
        file.seek(0)
        return file.read()


def _parameter_cloudpickle(args, kwargs):
    from joblib.externals.cloudpickle import dumps
    return dumps((args, kwargs))


# original_init_ = Process.__init__
#
#
# def punched_init_(self, group=None, target=None, name=None, args=(), kwargs={}):
#     if target:
#         run = mlflow.active_run()
#         if run:
#             @wraps(target)
#             def new_target(*args, _pypads=None, _pypads_active_run_id=None, _pypads_tracking_uri=None, _pypads_affected_modules=None, **kwargs):
#                 import mlflow
#                 import pypads.base
#                 pypads.base.current_pads = _pypads
#                 mlflow.set_tracking_uri(_pypads_tracking_uri)
#                 mlflow.start_run(run_id=_pypads_active_run_id)
#                 _pypads.activate_tracking(reload_warnings=False, affected_modules=_pypads_affected_modules, clear_imports=True)
#                 out = target(*args, **kwargs)
#                 # TODO find other way to not close run after process finishes
#                 if len(mlflow.tracking.fluent._active_run_stack) > 0:
#                     mlflow.tracking.fluent._active_run_stack.pop()
#                 return out
#
#             target = new_target
#             kwargs["_pypads"] = current_pads
#             kwargs["_pypads_active_run_id"] = run.info.run_id
#             kwargs["_pypads_tracking_uri"] = mlflow.get_tracking_uri()
#             kwargs["_pypads_affected_modules"] = punched_module_names
#     return original_init_(*self, group=group, target=target, name=name, args=args, kwargs=kwargs)
#
#
# Process.__init__ = punched_init_

if is_package_available("joblib"):
    import joblib

    original_delayed = joblib.delayed


    @wraps(original_delayed)
    def punched_delayed(fn):
        """Decorator used to capture the arguments of a function."""

        @wraps(fn)
        def wrapped_function(*args, _pypads=None, _pypads_active_run_id=None, _pypads_tracking_uri=None,
                             _pypads_affected_modules=None, **kwargs):
            if _pypads:
                # noinspection PyUnresolvedReferences
                import pypads.base
                import mlflow

                is_own_process = not pypads.base.current_pads
                if is_own_process:
                    import pypads
                    # from cloudpickle import loads
                    # _pypads = loads(_pypads)
                    pypads.base.current_pads = _pypads
                    _pypads.activate_tracking(reload_warnings=False, affected_modules=_pypads_affected_modules,
                                              clear_imports=True)
                    # reactivate this run in the foreign process
                    mlflow.set_tracking_uri(_pypads_tracking_uri)
                    mlflow.start_run(run_id=_pypads_active_run_id, nested=True)

                    def clear_mlflow():
                        """
                        Don't close run. This function clears the run which was reactivated from the stack to stop a closing of it.
                        :return:
                        """
                        if len(mlflow.tracking.fluent._active_run_stack) == 1:
                            mlflow.tracking.fluent._active_run_stack.pop()

                    import atexit
                    atexit.register(clear_mlflow)

                from pickle import loads
                a, b = loads(args[0])

                # import pickle
                # a, b = pickle.loads(args[0])

                args = a
                kwargs = b

                out = fn(*args, **kwargs)
                if is_own_process:
                    return out, _pypads.cache
                else:
                    return out
            else:
                return fn(*args, **kwargs)

        def delayed_function(*args, **kwargs):
            run = mlflow.active_run()
            if run:
                from joblib.externals.cloudpickle import dumps
                # TODO only if this is going to be a process and not a thread (how can we know?)
                pickled_params = (_parameter_pickle(args, kwargs),)
                # kwargs = {"_pypads": dumps(current_pads), "_pypads_active_run_id": run.info.run_id,
                #           "_pypads_tracking_uri": mlflow.get_tracking_uri(),
                #           "_pypads_affected_modules": punched_module_names}
                kwargs = {"_pypads": current_pads, "_pypads_active_run_id": run.info.run_id,
                          "_pypads_tracking_uri": mlflow.get_tracking_uri(),
                          "_pypads_affected_modules": punched_module_names}
                args = pickled_params
            return wrapped_function, args, kwargs

        try:
            import functools
            delayed_function = functools.wraps(fn)(delayed_function)
        except AttributeError:
            " functools.wraps fails on some callable objects "
        return delayed_function


    setattr(joblib, "delayed", punched_delayed)

    original_call = joblib.Parallel.__call__


    @wraps(original_call)
    def joblib_call(self, *args, **kwargs):
        out = original_call(self, *args, **kwargs)
        if isinstance(out, List):
            real_out = []
            for entry in out:
                if isinstance(entry, tuple) and len(entry) == 2 and isinstance(entry[1], PypadsCache):
                    real_out.append(entry[0])
                    cache = entry[1]
                    pads = get_current_pads()
                    pads.cache.merge(cache)
                else:
                    real_out.append(entry)
            out = real_out
        return out


    setattr(joblib.Parallel, "__call__", joblib_call)

# --- Pypads App ---

# Default init_run fns
DEFAULT_INIT_RUN_FNS = [ISystem(), IRam(), ICpu(), IDisk(), IPid()]

# Default event mappings. We allow to log parameters, output or input
DEFAULT_LOGGING_FNS = {
    # "parameters": Parameter(),
    # "output": Output(_pypads_write_format=WriteFormats.text.name),
    # "input": Input(_pypads_write_format=WriteFormats.text.name),
    "hardware": {Cpu(), Ram(), Disk()},
    "metric": Metric(),
    # "autolog": MlflowAutologger(),
    # "pipeline": PipelineTracker(_pypads_pipeline_type="normal", _pypads_pipeline_args=False),
    "log": Log(),
    "init": LogInit()
}

# Default config.
# Pypads mapping files shouldn't interact directly with the logging functions,
# but define events on which different logging functions can listen.
# This config defines such a listening structure.
# {"recursive": track functions recursively. Otherwise check the callstack to only track the top level function.}
DEFAULT_CONFIG = {"events": {
    "init": {"on": ["pypads_init"]},
    "parameters": {"on": ["pypads_fit"]},
    "hardware": {"on": ["pypads_fit"]},
    "output": {"on": ["pypads_fit", "pypads_predict"]},
    "input": {"on": ["pypads_fit"], "with": {"_pypads_write_format": WriteFormats.text.name}},
    "metric": {"on": ["pypads_metric"]},
    "pipeline": {"on": ["pypads_fit", "pypads_predict", "pypads_transform", "pypads_metric"]},
    "log": {"on": ["pypads_log"]}
},
    "recursion_identity": False,
    "recursion_depth": -1,
    "log_on_failure": True}

# Tag name to save the config to in mlflow context.
CONFIG_NAME = "pypads.config"

"""
TODO keras:
Logs loss and any other metrics specified in the fit
    function, and optimizer data as parameters. Model checkpoints
    are logged as artifacts to a 'models' directory.
    EarlyStopping Integration with Keras Automatic Logging
    MLflow will detect if an ``EarlyStopping`` callback is used in a ``fit()``/``fit_generator()``
    call, and if the ``restore_best_weights`` parameter is set to be ``True``, then MLflow will
    log the metrics associated with the restored model as a final, extra step. The epoch of the
    restored model will also be logged as the metric ``restored_epoch``.
    This allows for easy comparison between the actual metrics of the restored model and
    the metrics of other models.
    If ``restore_best_weights`` is set to be ``False``,
    then MLflow will not log an additional step.
    Regardless of ``restore_best_weights``, MLflow will also log ``stopped_epoch``,
    which indicates the epoch at which training stopped due to early stopping.
    If training does not end due to early stopping, then ``stopped_epoch`` will be logged as ``0``.
    MLflow will also log the parameters of the EarlyStopping callback,
    excluding ``mode`` and ``verbose``.
"""


class PypadsApi:
    def __init__(self, pypads):
        self._pypads = pypads

    # noinspection PyMethodMayBeStatic
    def track(self, fn, ctx=None, events: List = None, mapping: AlgorithmMapping = None):
        if events is None:
            events = ["pypads_log"]
        if ctx is not None and not hasattr(ctx, fn.__name__):
            warning("Given context " + str(ctx) + " doesn't define " + str(fn.__name__))
            # TODO create dummy context
            ctx = None
        if mapping is None:
            warning("Tracking a function without a mapping definition. A default mapping will be generated.")
            if '__file__' in fn.__globals__:
                lib = fn.__globals__['__file__']
            else:
                lib = fn.__module__
            if ctx is not None:
                if hasattr(ctx, '__module__') and ctx.__module__ is not str.__class__.__module__:
                    ctx_path = ctx.__module__.__name__
                else:
                    ctx_path = ctx.__name__
            else:
                ctx_path = "<unbound>"

            # For all events we want to hook to
            hooks = [Hook(e) for e in events]
            mapping = AlgorithmMapping(ctx_path + "." + fn.__name__, lib, AlgorithmMeta(fn.__name__, []), None,
                                       hooks=hooks)
        from pypads.autolog.wrapping.wrapping import wrap
        return wrap(fn, ctx=ctx, mapping=mapping)

    def start_run(self, run_id=None, experiment_id=None, run_name=None, nested=False):
        out = mlflow.start_run(run_id=run_id, experiment_id=experiment_id, run_name=run_name, nested=nested)
        self._pypads.run_init_fns()
        return out

    # ---- logging ----
    def log_artifact(self, local_path, artifact_path, meta=None):
        mlflow.log_artifact(local_path=local_path, artifact_path=artifact_path)
        self._write_meta(_to_artifact_meta_name(os.path.basename(artifact_path)), meta)

    def log_mem_artifact(self, name, obj, write_format=WriteFormats.text.name, preserve_folder=True, meta=None):
        try_write_artifact(name, obj, write_format, preserve_folder)
        self._write_meta(_to_artifact_meta_name(name), meta)

    def log_metric(self, key, value, step=None, meta=None):
        mlflow.log_metric(key, value, step)
        self._write_meta(_to_metric_meta_name(key), meta)

    def log_param(self, key, value, meta=None):
        mlflow.log_param(key, value)
        self._write_meta(_to_param_meta_name(key), meta)

    def set_tag(self, key, value):
        return mlflow.set_tag(key, value)

    def _write_meta(self, name, meta):
        if meta:
            try_write_artifact(name + ".meta", meta, WriteFormats.text, preserve_folder=True)

    # !--- logging ----

    # ---- run management ----
    @contextmanager
    def intermediate_run(self, **kwargs):
        enclosing_run = mlflow.active_run()
        try:
            # TODO check if nested run is a good idea
            # if enclosing_run:
            #   mlflow.end_run()
            run = self._pypads.api.start_run(**kwargs, nested=True)
            self._pypads.cache.run_add("enclosing_run", enclosing_run)
            yield run
        finally:
            if not mlflow.active_run() is enclosing_run:
                self._pypads.cache.run_clear()
                self._pypads.cache.run_delete()
                mlflow.end_run()
                # try:
                #     mlflow.start_run(run_id=enclosing_run.info.run_id)
                # except Exception:
                #     mlflow.end_run()
                #     mlflow.start_run(run_id=enclosing_run.info.run_id)

    def _get_post_run(self):
        if not self._pypads.cache.run_exists("post_run_fns"):
            post_run_fn_cache = Cache()
            self._pypads.cache.run_add("post_run_fns", post_run_fn_cache)
        return self._pypads.cache.run_get("post_run_fns")

    def register_post_fn(self, name, fn, order=0):
        cache = self._get_post_run()
        if cache.exists(name):
            debug("Post run fn with name '" + name + "' already exists. Skipped.")
        else:
            cache.add(name, (fn, order))

    def active_run(self):
        return mlflow.active_run()

    def end_run(self):
        chached_fns = self._get_post_run()
        fn_list = [v for i, v in chached_fns.items()]
        fn_list.sort(key=lambda t: t[1])
        for fn, _ in fn_list:
            fn()
        # TODO alternatively punch mlflow end_run
        mlflow.end_run()
    # !--- run management ----


def _to_artifact_meta_name(name):
    return name + ".artifact"


def _to_metric_meta_name(name):
    return name + ".metric"


def _to_param_meta_name(name):
    return name + ".param"


class PypadsDecorators:
    def __init__(self, pypads):
        self._pypads = pypads

    def track(self, event="pypads_log", mapping: AlgorithmMapping = None):
        def track_decorator(fn):
            ctx = get_class_that_defined_method(fn)
            events = event if isinstance(event, List) else [event]
            return self._pypads.api.track(ctx=ctx, fn=fn, events=events, mapping=mapping)

        return track_decorator


class PyPads:
    """
    PyPads app. Enable automatic logging for all libs in mapping files.
    Serves as the main entrypoint to PyPads. After constructing this app tracking is activated.
    """

    def __init__(self, uri=None, name=None, mapping_paths=None, mapping=None, init_run_fns=None,
                 include_default_mappings=True,
                 logging_fns=None, config=None, reload_modules=False, affected_modules=None):
        """
        TODO
        :param uri:
        :param name:
        :param logging_fns:
        :param config:
        :param mod_globals:
        """

        global current_pads
        current_pads = self

        if mapping_paths is None:
            mapping_paths = []

        if init_run_fns is None:
            init_run_fns = DEFAULT_INIT_RUN_FNS

        self._api = PypadsApi(self)
        self._decorators = PypadsDecorators(self)
        self._cache = PypadsCache()
        self._call_tracker = CallTracker(self)

        self._init_run_fns = init_run_fns
        self._init_mlflow_backend(uri, name, config)
        self._function_registry = FunctionRegistry(logging_fns or DEFAULT_LOGGING_FNS)
        self._init_mapping_registry(*mapping_paths, mapping=mapping, include_defaults=include_default_mappings)
        self.activate_tracking(reload_modules=reload_modules, affected_modules=affected_modules)

    def activate_tracking(self, reload_modules=False, reload_warnings=True, clear_imports=False, affected_modules=None):
        """
        Function to duck punch all objects defined in the mapping files. This should at best be called before importing
        any libraries.
        :param mod_globals: globals() object used to duckpunch already loaded classes
        :return:
        """
        if affected_modules is None:
            affected_modules = punched_module_names | self.mapping_registry.get_libraries()

        def _is_affected_module(name):
            affected = set([module.split(".", 1)[0] for module in affected_modules])
            return any([name.startswith(module + ".") or name == module for module in affected]) or any(
                [name.startswith(module + ".") or name == module for module in
                 affected_modules])

        global tracking_active
        if not tracking_active:

            # Add our loader to the meta_path
            extend_import_module()

            import sys
            import importlib
            loaded_modules = [(name, module) for name, module in sys.modules.items()]
            for name, module in loaded_modules:
                if _is_affected_module(name):
                    if reload_warnings:
                        warning(
                            name + "was imported before PyPads. To enable tracking import PyPads before or use "
                                   "reload_modules. Every already created instance is not tracked.")

                    if reload_modules:
                        try:
                            spec = importlib.util.find_spec(module.__name__)
                            duck_punch_loader(spec)
                            loader = spec.loader
                            module = loader.load_module(module.__name__)
                            loader.exec_module(module)
                            importlib.reload(module)
                        except Exception as e:
                            debug("Couldn't reload module " + str(e))

                    if clear_imports:
                        del sys.modules[name]
            tracking_active = True

    def _init_mlflow_backend(self, uri=None, name=None, config=None):
        """
        Intialize the mlflow backend experiment and run as well as store the config to it.
        :param uri:
        :param name:
        :param config:
        :return:
        """
        self._uri = uri or os.environ.get('MLFLOW_PATH') or 'file:' + os.path.expanduser('~/.mlruns')
        mlflow.set_tracking_uri(self._uri)

        # check if there is already an active run
        run = mlflow.active_run()
        if run is None:
            # Create run if run doesn't already exist
            name = name or "Default-PyPads"
            experiment = mlflow.get_experiment_by_name(name)
            experiment_id = experiment.experiment_id if experiment else mlflow.create_experiment(name)
            run = self.api.start_run(experiment_id=experiment_id)
        else:
            # Run init functions if run already exists but tracking is starting for it now
            self.run_init_fns()
        self._mlf = MlflowClient(self._uri)
        self._experiment = self.mlf.get_experiment_by_name(name) if name else self.mlf.get_experiment(
            run.info.experiment_id)
        if config:
            self.config = dict_merge({"events": {}}, DEFAULT_CONFIG, config)
        else:
            self.config = dict_merge({"events": {}}, DEFAULT_CONFIG)

        # override active run if used
        if name and run.info.experiment_id is not self._experiment.experiment_id:
            warning("Active run doesn't match given input name " + name + ". Recreating new run.")
            try:
                self.api.start_run(experiment_id=self._experiment.experiment_id)
            except Exception:
                mlflow.end_run()
                self.api.start_run(experiment_id=self._experiment.experiment_id)

    def _init_mapping_registry(self, *paths, mapping=None, include_defaults=True):
        """
        Function to initialize the mapping file registry
        :param paths:
        :param mapping:
        :param include_defaults:
        :return:
        """
        mapping_file_paths = []
        if include_defaults:
            # Use our with the package delivered mapping files
            mapping_file_paths.extend(glob.glob(os.path.join(expanduser("~"), ".pypads", "bindings", "**.json")))
            mapping_file_paths.extend(glob.glob(
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "bindings", "resources", "mapping", "**.json"))))
        if paths:
            mapping_file_paths.extend(paths)
        self._mapping_registry = MappingRegistry(*mapping_file_paths)
        if mapping:
            if isinstance(mapping, dict):
                for key, mapping in mapping.items():
                    self._mapping_registry.add_mapping(mapping, key=key)
            else:
                self._mapping_registry.add_mapping(mapping, key=id(mapping))

    @property
    def mapping_registry(self):
        return self._mapping_registry

    @property
    def mlf(self) -> MlflowClient:
        return self._mlf

    @property
    def function_registry(self) -> FunctionRegistry:
        return self._function_registry

    @property
    def config(self):
        return ast.literal_eval(self.mlf.get_run(mlflow.active_run().info.run_id).data.tags[CONFIG_NAME])

    @config.setter
    def config(self, value: dict):
        mlflow.set_tag(CONFIG_NAME, value)

    @property
    def experiment(self):
        return self._experiment

    @experiment.setter
    def experiment(self, value):
        # noinspection PyAttributeOutsideInit
        self._experiment = value

    @property
    def experiment_id(self):
        return self.experiment.experiment_id

    @property
    def api(self):
        return self._api

    @property
    def decorators(self):
        return self._decorators

    @property
    def call_tracker(self):
        return self._call_tracker

    @property
    def cache(self):
        return self._cache

    def run_init_fns(self):
        for fn in self._init_run_fns:
            if callable(fn):
                fn(self)


def get_current_pads() -> PyPads:
    """
    Get the currently active pypads instance. All duck punched objects use this function for interacting with pypads.
    :return:
    """
    global current_pads
    if not current_pads:
        # Try to reload pads if it was already defined in the active run
        config = get_current_config()

        if config:
            warning(
                "PyPads seems to be missing on given run with saved configuration. Reinitializing.")
            return PyPads(config=config)
        else:
            warning(
                "PyPads has to be initialized before logging can be used. Initializing for your with default values.")
            return PyPads()
    return current_pads


# Cache configs for runs. Each run could is for now static in it's config.
configs = {}

# --- Clean the config cache after run ---
original_end = mlflow.end_run


def end_run(*args, **kwargs):
    configs.clear()
    return original_end(*args, **kwargs)


mlflow.end_run = end_run


# !--- Clean the config cache after run ---


def get_current_config(default=None):
    """
    Get configuration defined in the current mlflow run
    :return:
    """
    global configs
    active_run = mlflow.active_run()
    if active_run in configs.keys():
        return configs[active_run]
    if not active_run:
        return default
    run = mlflow.get_run(active_run.info.run_id)
    if CONFIG_NAME in run.data.tags:
        configs[active_run] = ast.literal_eval(run.data.tags[CONFIG_NAME])
        return configs[active_run]
    return default


# --- Enfore end_run() at code exit ---
def cleanup():
    pads: PyPads = get_current_pads()
    if pads.api.active_run():
        pads.api.end_run()


atexit.register(cleanup)
