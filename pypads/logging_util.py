import os
import pickle
import shutil
import threading
from collections.__init__ import OrderedDict
from enum import Enum
from logging import warning
from os.path import expanduser

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.utils.autologging_utils import try_mlflow_log


def get_base_folder():
    """
    Get the base folder to log tmp files to. For now it can't be changed. TODO
    :return:
    """
    run = mlflow.active_run()
    if run is None:
        raise ValueError("No active run is defined.")
    return os.path.join(expanduser("~"), ".pypads", run.info.experiment_id, run.info.run_id) + os.path.sep


# --- Clean tmp files after run ---
original_end = mlflow.end_run


def end_run(*args, **kwargs):
    folder = get_base_folder()
    if os.path.exists(folder):
        shutil.rmtree(folder)
    return original_end(*args, **kwargs)


mlflow.end_run = end_run
# !--- Clean tmp files after run ---


class WriteFormats(Enum):
    pickle = 1
    text = 2


# extract all tags of runs by experiment id
def all_tags(experiment_id):
    client = MlflowClient(mlflow.get_tracking_uri())
    ds_infos = client.list_run_infos(experiment_id)
    for i in ds_infos:
        yield mlflow.get_run(i.run_id).data.tags


def try_write_artifact(file_name, obj, write_format, preserve_folder=True):
    """
    Function to write an artifact to disk. TODO
    :param write_format:
    :param file_name:
    :param obj:
    :return:
    """
    base_path = get_base_folder()
    path = base_path + file_name

    # Todo allow for configuring output format
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    # Functions for the options to write to
    def write_text(p, o):
        with open(p + ".txt", "w+") as fd:
            fd.write(str(o))
            return fd.name

    def write_pickle(p, o):
        try:
            with open(p + ".pickle", "wb+") as fd:
                pickle.dump(o, fd)
                return fd.name
        except Exception as e:
            warning("Couldn't pickle output. Trying to save toString instead. " + str(e))
            return write_text(p, o)

    # Options to write to
    options = {
        WriteFormats.pickle: write_pickle,
        WriteFormats.text: write_text
    }

    # Write to disk
    if isinstance(write_format, str):
        if WriteFormats[write_format]:
            write_format = WriteFormats[write_format]
        else:
            warning("Configured write format " + write_format + " not supported! ")
            return

    path = options[write_format](path, obj)
    if preserve_folder:
        in_folder = os.path.join(base_path, file_name.split(os.sep)[0])
        # Log artifact to mlflow
        if os.path.isdir(in_folder):
            try_mlflow_log(mlflow.log_artifact, in_folder)
        else:
            try_mlflow_log(mlflow.log_artifact, path)
    else:
        try_mlflow_log(mlflow.log_artifact, path)


def get_current_call_dict(self, ctx, wrapped):
    from pypads.base import get_current_pads
    pads = get_current_pads()
    call_objects: dict = pads.cache.run_get("call_objects")
    if call_objects is None:
        raise ValueError("Call objects have to be tracked before a call dict can be extracted.")
    function_calls: OrderedDict = call_objects[get_function_id(ctx, wrapped)]
    call_items = list(function_calls.items())
    instance_id = get_instance_id(self)

    instance_number = -1
    call_number = -1
    for instance_number in range(0, len(call_items)):
        # noinspection PyUnresolvedReferences
        key, value = call_items[instance_number]
        if key == instance_id:
            return value[-1]


def get_current_call_str(self, ctx, wrapped):
    from pypads.base import get_current_pads
    pads = get_current_pads()
    call_objects: dict = pads.cache.run_get("call_objects")
    if call_objects is None:
        raise ValueError("Call objects have to be tracked before a call str can be extracted.")
    function_calls: OrderedDict = call_objects[get_function_id(ctx, wrapped)]
    call_items = list(function_calls.items())
    instance_id = get_instance_id(self)

    instance_number = -1
    call_number = -1
    for instance_number in range(0, len(call_items)):
        # noinspection PyUnresolvedReferences
        key, value = call_items[instance_number]
        if key == instance_id:
            call_number = len(value)
            break

    from pypads.functions.analysis.call_objects import _get_local_index
    return "thread_" + str(
        threading.get_ident()) + "." + "context_" + ctx.__name__ + ".instance_" + str(
        instance_number) + "." + "function_" + wrapped.__name__ + ".call_" + str(
        _get_local_index(str(id(get_current_call_dict(self, ctx, wrapped)))))


def get_current_call_folder(self, ctx, wrapped):
    from pypads.base import get_current_pads
    pads = get_current_pads()
    call_objects: dict = pads.cache.run_get("call_objects")
    if call_objects is None:
        raise ValueError("Call objects have to be tracked before a call folder can be extracted.")
    function_calls: OrderedDict = call_objects[get_function_id(ctx, wrapped)]
    call_items = list(function_calls.items())
    instance_id = get_instance_id(self)

    instance_number = -1
    call_number = -1
    for instance_number in range(0, len(call_items)):
        # noinspection PyUnresolvedReferences
        key, value = call_items[instance_number]
        if key == instance_id:
            call_number = len(value)
            break

    from pypads.functions.analysis.call_objects import _get_local_index
    return os.path.join("thread_" + str(threading.get_ident()), "context_" + ctx.__name__,
                        "instance_" + str(instance_number), "function_" + wrapped.__name__,
                        "call_" + str(_get_local_index(str(id(get_current_call_dict(self, ctx, wrapped))))))


def get_function_id(ctx, wrapped):
    if hasattr(wrapped, "__name__"):
        if hasattr(ctx, wrapped.__name__):
            return id(getattr(ctx, wrapped.__name__))
    return str(id(ctx)) + "." + str(id(wrapped))


def get_instance_id(self):
    return id(self)
