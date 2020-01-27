import datetime
import os
from logging import warning
from types import FunctionType

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads.autolog.pypads_import import activate_tracking, try_write_artifact
from pypads.bindings.generic_visitor import default_visitor


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
            warning("Function call with name " + name + " is not linked with any logging functionality.")

    def add_function(self, name, fn: FunctionType):
        self.fns[name] = fn


def get_now():
    """
    Function for providing a current human readable timestamp.
    :return: timestamp
    """
    return datetime.datetime.now().strftime("%d_%b_%Y_%H-%M-%S.%f")


def parameters(self, *args, pypads_wrappe, pypads_package, pypads_item, pypads_fn_stack, **kwargs):
    """
    Function logging the parameters of the current pipeline object function call.
    :param self: Wrapper library object
    :param args: Input args to the real library call
    :param pypads_wrappe: pypads provided - wrapped library object
    :param pypads_package: pypads provided - wrapped library package
    :param pypads_item: pypads provided - wrapped function name
    :param pypads_fn_stack: pypads provided - stack of all the next functions to execute
    :param kwargs: Input kwargs to the real library call
    :return:
    """
    result = pypads_fn_stack.pop()(*args, **kwargs)
    # prevent wrapped_class from becoming unwrapped
    visitor = default_visitor(self)

    for k, v in visitor[0]["steps"][0]["hyper_parameters"]["model_parameters"].items():
        try_mlflow_log(mlflow.log_param, pypads_package + "." + str(id(self)) + "." + get_now() + "." + k, v)
    if self is not None:
        if result is self._pads_wrapped_instance:
            return self
    return result


def output(self, *args, pypads_wrappe, pypads_package, pypads_item, pypads_fn_stack, **kwargs):
    """
    Function logging the output of the current pipeline object function call.
    :param self: Wrapper library object
    :param args: Input args to the real library call
    :param pypads_wrappe: pypads provided - wrapped library object
    :param pypads_package: pypads provided - wrapped library package
    :param pypads_item: pypads provided - wrapped function name
    :param pypads_fn_stack: pypads provided - stack of all the next functions to execute
    :param kwargs: Input kwargs to the real library call
    :return:
    """
    result = pypads_fn_stack.pop()(*args, **kwargs)
    name = pypads_wrappe.__name__ + "." + str(id(self)) + "." + get_now() + "." + pypads_item + "_output"
    try_write_artifact(name, result)
    if self is not None:
        if result is self._pads_wrapped_instance:
            return self
    return result


def input(self, *args, pypads_wrappe, pypads_package, pypads_item, pypads_fn_stack, **kwargs):
    """
    Function logging the input parameters of the current pipeline object function call.
    :param self: Wrapper library object
    :param args: Input args to the real library call
    :param pypads_wrappe: pypads provided - wrapped library object
    :param pypads_package: pypads provided - wrapped library package
    :param pypads_item: pypads provided - wrapped function name
    :param pypads_fn_stack: pypads provided - stack of all the next functions to execute
    :param kwargs: Input kwargs to the real library call
    :return:
    """
    for i in range(len(args)):
        arg = args[i]
        name = pypads_wrappe.__name__ + "." + str(id(self)) + "." + get_now() + "." + pypads_item + "_input_" + str(
            i) + ".bin"
        try_write_artifact(name, arg)

    for (k, v) in kwargs.items():
        name = pypads_wrappe.__name__ + "." + str(
            id(self)) + "." + get_now() + "." + pypads_item + "_input_" + k + ".txt"
        try_write_artifact(name, v)

    result = pypads_fn_stack.pop()(*args, **kwargs)
    if self is not None:
        if result is self._pads_wrapped_instance:
            return self
    return result


def metric(self,*args, pypads_wrappe, pypads_package, pypads_item, pypads_fn_stack, **kwargs):
    """
    Function logging the wrapped metric function
    :param self: Wrapper library object
    :param args: Input args to the real library call
    :param pypads_wrappe: pypads provided - wrapped library object
    :param pypads_package: pypads provided - wrapped library package
    :param pypads_item: pypads provided - wrapped function name
    :param pypads_fn_stack: pypads provided - stack of all the next functions to execute
    :param kwargs: Input kwargs to the real library call
    :return:
    """
    result = pypads_fn_stack.pop()(*args, **kwargs)
    try_mlflow_log(mlflow.log_metric, pypads_item, result)
    if self is not None:
        if result is self._pads_wrapped_instance:
            return self
    return result

# Default mappings. We allow to log parameters, output or input
DEFAULT_MAPPING = {
    "parameters": parameters,
    "output": output,
    "input": input,
    "metric": metric
}

# Default config.
# Pypads mapping files shouldn't interact directly with the logging functions,
# but define events on which different logging functions can listen.
# This config defines such a listening structure.
DEFAULT_CONFIG = {"events": {
    "parameters": ["pypads_fit"],
    "cpu": [],
    "output": ["pypads_fit", "pypads_predict","pypads_metric"],
    "input": ["pypads_fit","pypads_metric"],
    "metric": ["pypads_metric"]
}}

# Tag name to save the config to in mlflow context.
CONFIG_NAME = "pypads.config"


class PyPads:
    """
    PyPads app. Serves as the main entrypoint to PyPads. After constructing this app tracking is activated..
    """
    current_pads = None

    def __init__(self, uri=None, name=None, mapping=None, config=None, mod_globals=None):
        """
        TODO
        :param uri:
        :param name:
        :param mapping:
        :param config:
        :param mod_globals:
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
        self._function_registry = FunctionRegistry(mapping or DEFAULT_MAPPING)
        self._experiment = self.mlf.get_experiment_by_name(name)
        self.config = config or DEFAULT_CONFIG

        # override active run if used
        if name and run.info.experiment_id is not self.mlf.get_experiment_by_name(name).experiment_id:
            warning("Active run doesn't match given input name " + name + ". Recreating new run.")
            self._run = mlflow.start_run(experiment_id=self._experiment.info.experiment_id)
        else:
            self._run = run

        activate_tracking(mod_globals=mod_globals)
        PyPads.current_pads = self

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


def get_current_pads() -> PyPads:
    """
    Get the currently active pypads instance. All duck punched objects use this function for interacting with pypads.
    :return:
    """
    if not PyPads.current_pads:
        warning("PyPads has to be initialized before logging can be used. Initializing for your with default values.")
        PyPads()
    return PyPads.current_pads
