from logging import warning
from types import GeneratorType
import mlflow
from boltons.funcutils import wraps
from mlflow.utils.autologging_utils import try_mlflow_log
from pypads.autolog.mapping import Mapping
from pypads.base import PyPads, PypadsApi, PypadsDecorators
from pypads.mlflow.mlflow_autolog import autologgers
from pypads.pipeline.pipeline_detection import pipeline
from pypadsext.util import get_class_that_defined_method
from pypads.validation.logging_functions import parameters
from typing import List
from pypadsext.logging_functions import dataset, predictions
from pypads.logging_functions import _get_now, output, input, cpu, metric, log
from pypads.logging_util import try_write_artifact, WriteFormats

# --- Pypads App ---

# Extended mappings. We allow to log parameters, output or input, datasets
EXT_MAPPING = {
    "parameters": parameters,
    "output": output,
    "input": input,
    "cpu": cpu,
    "metric": metric,
    "autolog": autologgers,
    "pipeline": pipeline,
    "log": log,
    "dataset": dataset,
    "predictions" : predictions
}

# Extended config.
# Pypads mapping files shouldn't interact directly with the logging functions,
# but define events on which different logging functions can listen.
# This config defines such a listening structure.
# {"recursive": track functions recursively. Otherwise check the callstack to only track the top level function.}
EXT_CONFIG = {"events": {
    "parameters": {"on": ["pypads_fit"]},
    "cpu": {"on": ["pypads_fit"]},
    "output": {"on": ["pypads_fit", "pypads_predict"],
               "with": {"write_format": WriteFormats.text.name}},
    "input": {"on": ["pypads_fit"], "with": {"write_format": WriteFormats.text.name}},
    "metric": {"on": ["pypads_metric"]},
    "pipeline": {"on": ["pypads_fit", "pypads_predict", "pypads_transform", "pypads_metric"],
                 "with": {"pipeline_type": "normal", "pipeline_args": False}},
    "log": {"on": ["pypads_log"]},
    "dataset": {"on": ["pypads_data"]},
    "predictions": {"on": ["pypads_predict"]}
},
    "recursion_identity": False,
    "recursion_depth": -1,
    "retry_on_fail": True}

# Tag name to save the config to in mlflow context.
CONFIG_NAME = "pypads.config"


class PyPadsEXT(PyPads):
    def __init__(self, *args, config=None, mapping=None, **kwargs):
        self._cache = dict()
        config = config or EXT_CONFIG
        mapping = mapping or EXT_MAPPING
        super().__init__(*args, config=config, mapping=mapping, **kwargs)
        PyPads.current_pads = self
        self._api = PypadsApi(self)
        self._decorators = PypadsDecorators(self)

    # ------------------------------------------- public API methods ------------------------
    def run_id(self):
        return self.run.info.run_id

    def experiment_id(self):
        return self.experiment.experiment_id

    def active_run(self):
        return mlflow.active_run() and mlflow.active_run().info.run_id == self.run_id()

    def start_run(self):
        if self.active_run():
            mlflow.end_run()
            self.run = mlflow.start_run(experiment_id=self._experiment.experiment_id)

    def stop_run(self):
        if self.active_run():
            mlflow.end_run()
        else:
            self._run = self.mlf.get_run(mlflow.active_run().info.run_id)
            mlflow.end_run()

    def resume_run(self):
        try:
            mlflow.start_run(run_id=self.run_id())
        except Exception:
            mlflow.end_run()
            mlflow.start_run(run_id=self.run_id())

    @property
    def cache(self):
        return self._cache

    def add(self, key, value):
        if key in self.cache:
            if isinstance(value, dict):
                self.cache.get(key).update(value)
            else:
                warning("The given value has no defining key besides the run id!")
        else:
            self.cache.update({key: value})

    def pop(self, key):
        if key in self.cache:
            return self.cache.pop(key)
        return None

    # ------------------------------------------- decorators --------------------------------
    def dataset(self, event="pypads_data", mapping: Mapping = None, name=None, metadata=None):
        def dataset_decorator(fn):
            ctx = get_class_that_defined_method(fn)
            events = event if isinstance(event, List) else [event]
            return self.api.track(ctx=ctx, fn=fn, events=events, mapping=mapping)
        if name:
            self.add(self.run_id, {'dataset_name':name})
        if metadata:
            self.add(self.run_id, {'dataset_meta': metadata})
        return dataset_decorator

    def splitter(self, dataset=None):
        def decorator(f_splitter):
            @wraps(f_splitter)
            def wrapper(*args, **kwargs):
                splits = f_splitter(*args, **kwargs)
                ds_name = self.cache.get("dataset_name", dataset)
                ds_id = self.cache.get("dataset_id", None)
                run_id = self.run.info.run_id

                def log_split(num, train_idx, test_idx, targets=None):
                    self.add(run_id, {
                        str(num): {'dataset': ds_name, 'dataset_id': ds_id, 'train_indices': train_idx,
                                   'test_indices': test_idx}})

                    if targets is not None:
                        self.cache.get(run_id).get(str(num)).update(
                            {'predictions': {str(sample): {'truth': targets[i]} for i, sample in
                                             enumerate(test_idx)}})
                    else:
                        warning(
                            "Your splitter does not provide targets information, Truth values will be missing from "
                            "the logged predictions")
                    name = 'Split_{}_{}_information.txt'.format(num, _get_now())
                    try_write_artifact(name,
                                       {'dataset': ds_name, 'train_indices': train_idx, 'test_indices': test_idx},
                                       WriteFormats.text)
                    self.cache.get(run_id).update({"curr_split": num})

                if isinstance(splits, GeneratorType):
                    for num, train_idx, test_idx, targets in splits:
                        log_split(num, train_idx, test_idx, targets=targets)
                        yield num, train_idx, test_idx
                else:
                    num, train_idx, test_idx, targets = splits
                    log_split(num, train_idx, test_idx, targets=targets)
                    return num, train_idx, test_idx

            return wrapper

        return decorator

    # noinspection PyMethodMayBeStatic
    def grid_search(self):
        def decorator(f_grid):
            @wraps(f_grid)
            def wrapper(*args, **kwargs):
                parameters = f_grid(*args, **kwargs)

                import itertools
                master_list = []
                params_list = []
                for params in parameters:
                    param = parameters.get(params)
                    if not isinstance(param, list):
                        param = [param]
                    master_list.append(param)
                    params_list.append(params)

                grid = itertools.product(*master_list)

                for element in grid:
                    execution_params = dict()
                    for param, idx in zip(params_list, range(0, len(params_list))):
                        execution_params[param] = element[idx]
                        try_mlflow_log(mlflow.log_param, "Grid_params." + param + ".txt", element[idx])
                    name = "Grid_params_{}".format(_get_now())
                    try_write_artifact(name, execution_params, WriteFormats.text)
                    yield execution_params

            return wrapper

        return decorator


def get_current_pads() -> PyPadsEXT:
    """
        Get the currently active pypads instance. All duck punched objects use this function for interacting with pypads.
        :return:
        """
    if not PyPadsEXT.current_pads:
        warning("PyPads has to be initialized before logging can be used. Initializing for your with default values.")
        PyPadsEXT()
    return PyPadsEXT.current_pads