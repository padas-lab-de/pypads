import os
import tempfile
from functools import wraps
from types import GeneratorType
from typing import Tuple
import mlflow
from pypads.logging_functions import get_now

from pypads.logging_util import try_write_artifact, WriteFormats, all_tags


def unpack(kwargs_obj: dict, *args):
    """
    Unpacks a dict object into a tuple. You can pass tuples for setting default values.
    :param kwargs_obj:
    :param args:
    :return:
    """
    empty = object()
    arg_list = []
    for entry in args:
        if isinstance(entry, str):
            arg_list.append(kwargs_obj.get(entry))
        elif isinstance(entry, Tuple):
            key, *rest = entry
            default = empty if len(rest) == 0 else rest[0]
            if default is empty:
                arg_list.append(kwargs_obj.get(key))
            else:
                arg_list.append(kwargs_obj.get(key, default))
        else:
            raise ValueError("Pass a tuple or string not: " + str(entry))
    return tuple(arg_list)


def split_tracking(cache=None):
    run = mlflow.active_run()
    if cache is None:
        cache = {run.id: dict()}

    def decorator(f_splitter):
        @wraps(f_splitter)
        def wrapper(*args, **kwargs):
            splits = f_splitter(*args, **kwargs)
            data = args[0]
            if isinstance(splits, GeneratorType):
                for num, train_idx, test_idx in splits:
                    cache[run.id].update(
                        {str(num): {'dataset': data.name, 'train_indices': train_idx, 'test_indices': test_idx}})
                    cache.get(str(num)).update(
                        {'predictions': {str(sample): {'truth': data.targets()[sample][0]} for sample in test_idx}})
                    name = 'Split_{}_{}_information.txt'.format(num, get_now())
                    try_write_artifact(name,
                                       {'dataset': data.name, 'train_indices': train_idx, 'test_indices': test_idx},
                                       WriteFormats.text)
                    yield num, train_idx, test_idx
            else:
                num, train_idx, test_idx = splits
                cache.update({str(num): {'train_indices': train_idx, 'test_indices': test_idx}})
                cache.get(str(num)).update(
                    {'predictions': {str(sample): {'truth': data.targets()[sample][0]} for sample in test_idx}})
                name = 'Split_{}_{}_information'.format(num, get_now())
                try_write_artifact(name,
                                   {'dataset': data.name, 'train_indices': train_idx, 'test_indices': test_idx},
                                   WriteFormats.text)
                return num, train_idx, test_idx

        return wrapper

    return decorator


def grid_search_tracking():
    def decorator(f_grid):
        @wraps(f_grid)
        def wrapper(*args, **kwargs):
            grid = f_grid(*args, **kwargs)

            for element in grid['grid']:
                execution_params = dict()
                for param, idx in zip(grid['parameters'], range(0, len(grid['parameters']))):
                    execution_params[param] = element[idx]
                name = "Grid_params_{}".format(get_now())
                try_write_artifact(name, execution_params, WriteFormats.text)
                yield execution_params

        return wrapper

    return decorator


# TODO work on the datasets tracking
DATASETS = "datasets"


def dataset(name=None, metadata=None):
    def dataset_decorator(f_create_dataset):
        @wraps(f_create_dataset)
        def wrap_dataset(*args, **kwargs):
            # TODO it may be better to hold an experiment for each dataset and runs for different versions of the same dataset
            dataset = f_create_dataset(*args, **kwargs)

            repo = mlflow.get_experiment_by_name(DATASETS)
            if repo is None:
                repo = mlflow.get_experiment(mlflow.create_experiment(DATASETS))

            # add data set if it is not already existing
            if not any(t["name"] == name for t in all_tags(repo.experiment_id)):
                if mlflow.active_run():
                    mlflow.end_run()
                run = mlflow.start_run(experiment_id=repo.experiment_id)
                mlflow.set_tag("name", dataset['name'])
                name_ = name + "_" + str(id(dataset)) + "_data"
                try_write_artifact(name_, dataset['data'], WriteFormats.pickle)
                if metadata:
                    name_ = name + "_" + str(id(dataset)) + "metadata"
                    try_write_artifact(name_, metadata, WriteFormats.text)
                mlflow.end_run()

            return dataset

        return wrap_dataset

    return dataset_decorator
