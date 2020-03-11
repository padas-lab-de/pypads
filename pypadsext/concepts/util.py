import functools
import hashlib
import operator
from typing import Tuple


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


def get_by_tag(tag=None, value=None, experiment_id=None):
    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()
    if not experiment_id:
        experiment_id = pads.api.active_run().info.experiment_id

    runs = pads.mlf.list_run_infos(experiment_id)
    selection = []
    for run in runs:
        run = pads.mlf.get_run(run.run_id)
        if tag:
            tags = run.data.tags
            if value and tag in tags:
                if tags[tag] == value:
                    selection.append(run)
            else:
                selection.append(run)
        else:
            selection.append(run)
    return selection
