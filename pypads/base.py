import os
from logging import warning
from types import FunctionType

import mlflow
from mlflow.tracking import MlflowClient

from pypads.autolog.hook import Hook
from pypads.autolog.mapping import Mapping
from pypads.autolog.wrapping import wrap
from pypads.logging_functions import parameters, output, input, cpu, metric, log
from pypads.logging_util import WriteFormats
from pypads.mlflow.mlflow_autolog import autologgers
from pypads.pipeline.pipeline_detection import pipeline
from pypads.util import get_class_that_defined_method


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

# Default mappings. We allow to log parameters, output or input
DEFAULT_MAPPING = {
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
    "pipeline": {"on": ["pypads_fit", "pypads_predict", "pypads_transform", "pypads_metric"],
                 "with": {"pipeline_type": "group"}},
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
    def track(self, fn, ctx=None, event="pypads_log", mapping: Mapping = None):
        if ctx is not None and not hasattr(ctx, fn.__name__):
            warning("Given context " + str(ctx) + " doesn't define " + str(fn.__name__))
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
            mapping = Mapping(ctx_path + "." + fn.__name__, lib, fn.__name__, None, hooks=[Hook(event)])
        return wrap(fn, ctx=ctx, mapping=mapping)


class PypadsDecorators:
    def __init__(self, pypads):
        self._pypads = pypads

    def track(self, event="pypads_log", mapping: Mapping = None):
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

    def __init__(self, uri=None, name=None, filter_mapping_files=None, mapping=None, config=None, mod_globals=None):
        """
        TODO
        :param uri:
        :param name:
        :param mapping:
        :param config:
        :param mod_globals:
        """
        if filter_mapping_files is None:
            filter_mapping_files = []
        self.filter_mapping_files = filter_mapping_files
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
        self._function_registry = FunctionRegistry(mapping or DEFAULT_MAPPING)
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
        PyPads.current_pads = self

        self._api = PypadsApi(self)
        self._decorators = PypadsDecorators(self)

        from pypads.autolog.pypads_import import activate_tracking
        activate_tracking(mod_globals=mod_globals)

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
