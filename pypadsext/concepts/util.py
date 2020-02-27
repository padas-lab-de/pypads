import functools
import hashlib
import operator
from typing import Tuple, Iterable

import mlflow
from mlflow.tracking import MlflowClient


def _create_ctx(cache):
    ctx = dict()
    if "data" in cache.keys():
        ctx["data"] = cache.get("data")
    if "shape" in cache.keys():
        ctx["shape"] = cache.get("shape")
    if "targets" in cache.keys():
        ctx["targets"] = cache.get("targets")
    return ctx


def persistent_hash(to_hash, algorithm=hashlib.md5):
    def add_str(a, b):
        return operator.add(str(persistent_hash(str(a), algorithm)), str(persistent_hash(str(b), algorithm)))

    if isinstance(to_hash, Tuple):
        to_hash = functools.reduce(add_str, to_hash)
    return int(algorithm(to_hash.encode("utf-8")).hexdigest(), 16)


def split_output_inv(result, fn=None):
    # function that looks into the output of the custom splitter
    split_info = dict()

    # Flag to check whether the outputs of the splitter are indices (one dimensional Iterable)
    indices = True
    if isinstance(result, Tuple):
        n_output = len(result)
        for a in result:
            if isinstance(a, Iterable):
                for row in a:
                    if isinstance(row, Iterable):
                        indices = False
                        break

        if n_output > 3:
            if indices:
                Warning(
                    'The splitter function return values are ambiguous (more than train/test/validation splitting).'
                    'Decision tracking might be inaccurate')
                split_info.update({'set_{}'.format(i): a for i, a in enumerate(result)})
                split_info.update({"decision_track": False})
            else:
                Warning("The output of the splitter is not indices, Decision tracking might be inaccurate.")
                if "sklearn" in fn.__module__:
                    split_info.update({'Xtrain': result[0], 'Xtest': result[1], 'ytrain': result[2],
                                       'ytest': result[3]})
                    split_info.update({"decision_track": True})
                else:
                    split_info.update({'output_{}'.format(i): a for i, a in enumerate(result)})
                    split_info.update({"decision_track": False})
        else:
            if indices:
                names = ['train', 'test', 'val']
                i = 0
                while i < n_output:
                    split_info[names[i]] = result[i]
                    i += 1
                split_info.update({"decision_track": True})
            else:
                Warning("The output of the splitter is not indices, Decision tracking might be inaccurate.")
                split_info.update({'output_{}'.format(i): a for i, a in enumerate(result)})
                split_info.update({"decision_track": False})
    else:
        Warning("The splitter has a single output. Decision tracking might be inaccurate.")
        split_info.update({'output_0': result})
        split_info.update({"decision_track": True})
    return split_info


def get_by_tag(tag=None, value=None, experiment_id=None):
    if not experiment_id:
        experiment_id = mlflow.active_run().info.experiment_id
    client = MlflowClient(mlflow.get_tracking_uri())
    runs = client.list_run_infos(experiment_id)
    selection = []
    for run in runs:
        run = client.get_run(run.run_id)
        if tag:
            tags = run.data.tags
            if value:
                if tags[tag] == value:
                    selection.append(run)
            else:
                selection.append(run)
        else:
            selection.append(run)
    return selection
