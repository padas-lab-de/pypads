import os
import tempfile
from functools import wraps
from types import GeneratorType
from typing import Tuple
import mlflow as mlf
from pypads.logging_functions import get_now

from pypads.logging_util import try_write_artifact, WriteFormats


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
    if cache is None:
        cache = dict()

    def decorator(f_splitter):
        @wraps(f_splitter)
        def wrapper(*args, **kwargs):
            splits = f_splitter(*args, **kwargs)
            data = args[0]
            if isinstance(splits, GeneratorType):
                for num, train_idx, test_idx in splits:
                    cache.update(
                        {str(num): {'dataset': data.name, 'train_indices': train_idx, 'test_indices': test_idx}})
                    cache.get(str(num)).update(
                        {'predictions': {str(sample): {'truth': data.targets()[sample][0]} for sample in test_idx}})
                    name = 'Split_{}_{}_information.txt'
                    try_write_artifact(name,
                                       {'dataset': data.name, 'train_indices': train_idx, 'test_indices': test_idx},
                                       WriteFormats.text)
                    yield num, train_idx, test_idx
            else:
                num, train_idx, test_idx = splits
                cache.update({str(num): {'train_indices': train_idx, 'test_indices': test_idx}})
                cache.get(str(num)).update(
                    {'predictions': {str(sample): {'truth': data.targets()[sample][0]} for sample in test_idx}})
                name = 'Split_{}_{}_information'.format(num,get_now())
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
            grid =  f_grid(*args,**kwargs)

        # grid = wrapper()

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
TMP = os.path.join(os.path.expanduser("~") + "/.pypads_tmp")

if not os.path.isdir(TMP):
    os.mkdir(TMP)


def dataset(*args, name=None, **kwargs):
    def dataset_decorator(f_create_dataset):
        @wraps(f_create_dataset)
        def wrap_dataset(*args, **kwargs):
            return f_create_dataset(*args, **kwargs)

        dataset = wrap_dataset()

        with tempfile.NamedTemporaryFile(dir=TMP) as fp:
            fp.write(str(dataset["data"]).encode())
            fp.seek(0)

            mlf.get_experiment_by_name()
            mlf.search_runs()

            # get default datasets experiment holding all datasets in form of runs
            # todo it may be better to hold an experiment for each dataset and runs for different versions of the same dataset
            repo = mlf.get_experiment_by_name(DATASETS)
            if repo is None:
                repo = mlf.get_experiment(mlf.create_experiment(DATASETS))

            # extract all tags of runs by experiment id
            def all_tags(experiment_id):
                ds_infos = mlf.list_run_infos(experiment_id)
                for i in ds_infos:
                    yield mlf.get_run(i.run_id).data.tags

            # add data set if it is not already existing
            if not any(t["name"] == dataset["name"] for t in all_tags(repo.experiment_id)):
                run = mlf.create_run(repo.experiment_id, tags={"name": dataset["name"]})
                mlf.log_artifact(run_id=run.info.run_id, local_path=os.path.join(TMP, fp.name), artifact_path="data")
                mlf.set_terminated(run_id=run.info.run_id)

    return dataset_decorator
