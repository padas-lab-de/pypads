import glob
import os
from logging import warning
from os.path import expanduser
from types import FunctionType
from typing import List

import mlflow
from mlflow.tracking import MlflowClient

from pypads.autolog.hook import Hook
from pypads.autolog.mappings import AlgorithmMapping, MappingRegistry, AlgorithmMeta
from pypads.autolog.wrapping import wrap
from pypads.logging_functions import output, input, cpu, metric, log
from pypads.logging_util import WriteFormats, try_write_artifact
from pypads.mlflow.mlflow_autolog import autologgers
from pypads.pipeline.pipeline_detection import pipeline
from pypads.util import get_class_that_defined_method
from pypads.validation.logging_functions import parameters


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
        self.fns = mapping

    def find_function(self, name):
        if name in self.fns:
            return self.fns[name]
        else:
            warning("Function call with name '" + name + "' is not linked with any logging functionality.")

    def add_function(self, name, fn: FunctionType):
        self.fns[name] = fn


# --- Pypads App ---

# Default event mappings. We allow to log parameters, output or input
DEFAULT_EVENT_MAPPING = {
    "parameters": parameters,
    "output": output,
    "input": input,
    "cpu": cpu,
    "metric": metric,
    "autolog": autologgers,
    "pipeline": pipeline,
    "log": log
}

# Default config.
# Pypads mapping files shouldn't interact directly with the logging functions,
# but define events on which different logging functions can listen.
# This config defines such a listening structure.
# {"recursive": track functions recursively. Otherwise check the callstack to only track the top level function.}
DEFAULT_CONFIG = {"events": {
    "parameters": {"on": ["pypads_fit"]},
    "cpu": {"on": ["pypads_fit"]},
    "output": {"on": ["pypads_fit", "pypads_predict"],
               "with": {"write_format": WriteFormats.text.name}},
    "input": {"on": ["pypads_fit"], "with": {"write_format": WriteFormats.text.name}},
    "metric": {"on": ["pypads_metric"]},
    "dataset": {"on": ["pypads_dataset"]},
    "pipeline": {"on": ["pypads_fit", "pypads_predict", "pypads_transform", "pypads_metric"],
                 "with": {"pipeline_type": "normal", "pipeline_args": False}},
    "log": {"on": ["pypads_log"]}
},
    "recursion_identity": False,
    "recursion_depth": -1,
    "retry_on_fail": True}

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
        return wrap(fn, ctx=ctx, mapping=mapping)

    def log_artifact(self, local_path, artifact_path, meta=None):
        mlflow.log_artifact(local_path=local_path, artifact_path=artifact_path)
        self._write_meta(os.path.basename(artifact_path), meta)

    def log_mem_artifact(self, name, obj, write_format=format, preserve_folder=True, meta=None):
        try_write_artifact(name, obj, write_format, preserve_folder)
        self._write_meta(name, meta)

    def log_metric(self, key, value, step=None, meta=None):
        mlflow.log_metric(key, value, step)
        self._write_meta(key + ".m", meta)

    def log_param(self, key, value, meta=None):
        mlflow.log_param(key, value)
        self._write_meta(key + ".p", meta)

    def _write_meta(self, name, meta):
        if meta:
            try_write_artifact(name + ".meta", meta, WriteFormats.text, preserve_folder=True)

    def end_run(self):
        # TODO pypads hooks instead of punching mlflow end_run
        mlflow.end_run()


class PypadsDecorators:
    def __init__(self, pypads):
        self._pypads = pypads

    def track(self, event="pypads_log", mapping: AlgorithmMapping = None):
        def track_decorator(fn):
            ctx = get_class_that_defined_method(fn)
            return self._pypads.api.track(ctx=ctx, fn=fn, event=event, mapping=mapping)

        return track_decorator


class PyPads:
    """
    PyPads app. Enable automatic logging for all libs in mapping files.
    Serves as the main entrypoint to PyPads. After constructing this app tracking is activated.
    """
    current_pads = None

    def __init__(self, uri=None, name=None, mapping_paths=None, mapping=None, include_default_mappings=True,
                 event_mapping=None, config=None,
                 mod_globals=None):
        """
        TODO
        :param uri:
        :param name:
        :param event_mapping:
        :param config:
        :param mod_globals:
        """

        if mapping_paths is None:
            mapping_paths = []

        self._init_mlflow_backend(uri, name, config)
        self._function_registry = FunctionRegistry(event_mapping or DEFAULT_EVENT_MAPPING)
        self._init_mapping_registry(*mapping_paths, mapping=mapping, include_defaults=include_default_mappings)
        PyPads.current_pads = self

        self._api = PypadsApi(self)
        self._decorators = PypadsDecorators(self)

        from pypads.autolog.pypads_import import activate_tracking
        activate_tracking(mod_globals=mod_globals)

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
            name = name or "Default-PyPads"
            experiment = mlflow.get_experiment_by_name(name)
            experiment_id = experiment.experiment_id if experiment else mlflow.create_experiment(name)
            run = mlflow.start_run(experiment_id=experiment_id)
        self._mlf = MlflowClient(self._uri)
        self._experiment = self.mlf.get_experiment_by_name(name) if name else self.mlf.get_experiment(
            run.info.experiment_id)
        if config:
            self.config = {**DEFAULT_CONFIG, **config}
        else:
            self.config = DEFAULT_CONFIG

        # override active run if used
        if name and run.info.experiment_id is not self._experiment.experiment_id:
            warning("Active run doesn't match given input name " + name + ". Recreating new run.")
            try:
                self._run = mlflow.start_run(experiment_id=self._experiment.experiment_id)
            except Exception:
                mlflow.end_run()
                self._run = mlflow.start_run(experiment_id=self._experiment.experiment_id)
        else:
            self._run = run

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
        return self.mlf.get_run(mlflow.active_run()).tag[CONFIG_NAME]

    @config.setter
    def config(self, value: dict):
        mlflow.set_tag(CONFIG_NAME, value)

    @property
    def run(self):
        return self._run

    @run.setter
    def run(self, value):
        self._run = value

    @property
    def experiment(self):
        return self._experiment

    @experiment.setter
    def experiment(self, value):
        self._experiment = value

    @property
    def api(self):
        return self._api

    @property
    def decorators(self):
        return self._decorators


def get_current_pads() -> PyPads:
    """
    Get the currently active pypads instance. All duck punched objects use this function for interacting with pypads.
    :return:
    """
    if not PyPads.current_pads:
        warning("PyPads has to be initialized before logging can be used. Initializing for your with default values.")
        PyPads()
    return PyPads.current_pads
