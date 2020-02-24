from logging import warning
from types import GeneratorType
from typing import List

import mlflow
from babel.messages.extract import DEFAULT_MAPPING
from boltons.funcutils import wraps
from mlflow.utils.autologging_utils import try_mlflow_log
from pypads import util
from pypads.autolog.mappings import AlgorithmMapping
from pypads.base import PyPads, PypadsApi, PypadsDecorators, DEFAULT_CONFIG
from pypads.logging_functions import _get_now
from pypads.logging_util import try_write_artifact, WriteFormats

from pypadsext.logging_functions import dataset, predictions
from pypadsext.util import get_class_that_defined_method

# --- Pypads App ---

# Extended mappings. We allow to log parameters, output or input, datasets
DEFAULT_PYPADRE_MAPPING = {
    "dataset": dataset,
    "predictions": predictions
}

# Extended config.
# Pypads mapping files shouldn't interact directly with the logging functions,
# but define events on which different logging functions can listen.
# This config defines such a listening structure.
# {"recursive": track functions recursively. Otherwise check the callstack to only track the top level function.}
DEFAULT_PYPADRE_CONFIG = {"events": {
    "dataset": {"on": ["pypads_dataset"]},
    "predictions": {"on": ["pypads_predict"]}
}}


class PyPadrePadsApi(PypadsApi):

    def __init__(self, pypads):
        super().__init__(pypads)

    def track_dataset(self, fn, ctx=None, name=None, metadata=None, mapping: AlgorithmMapping = None):
        if metadata is None:
            metadata = {}
        self._pypads.cache.run_add('dataset_name', name)
        self._pypads.cache.run_add('dataset_meta', metadata)
        return self.track(fn, ctx, ["pypads_dataset"], mapping=mapping)

    # TODO add as api and then use it in the decorators


class PyPadrePadsDecorators(PypadsDecorators):
    # ------------------------------------------- decorators --------------------------------
    def dataset(self, mapping=None, name=None, metadata=None):
        def track_decorator(fn):
            ctx = get_class_that_defined_method(fn)
            return self._pypads.api.track_dataset(ctx=ctx, fn=fn, name=name, metadata=metadata, mapping=mapping)

        return track_decorator

    def splitter(self, dataset=None):
        def decorator(f_splitter):
            @wraps(f_splitter)
            def wrapper(*args, **kwargs):
                splits = f_splitter(*args, **kwargs)
                ds_name = self._pypads.run_cache.get("dataset_name", dataset)
                ds_id = self._pypads.run_cache.get("dataset_id", None)
                run_id = self._pypads.run.info.run_id

                def log_split(num, train_idx, test_idx, targets=None):
                    self._pypads.run_cache.add(run_id, {
                        str(num): {'dataset': ds_name, 'dataset_id': ds_id, 'train_indices': train_idx,
                                   'test_indices': test_idx}})

                    if targets is not None:
                        self._pypads.cache.get(run_id).get(str(num)).update(
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
                    self._pypads.run_cache.get(run_id).update({"curr_split": num})

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


class PyPadrePads(PyPads):
    def __init__(self, *args, config=None, event_mapping=None, **kwargs):
        config = config or util.dict_merge(DEFAULT_CONFIG, DEFAULT_PYPADRE_CONFIG)
        event_mapping = event_mapping or util.dict_merge(DEFAULT_MAPPING, DEFAULT_PYPADRE_MAPPING)
        super().__init__(*args, config=config, event_mapping=event_mapping, **kwargs)
        self._api = PyPadrePadsApi(self)
        self._decorators = PyPadrePadsDecorators(self)
