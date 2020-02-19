import os
import pickle
import shutil
from enum import Enum
from logging import warning
from os.path import expanduser

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads.util import to_string


def to_folder(file_name):
    """
    TODO
    :param file_name:
    :return:
    """
    run = mlflow.active_run()
    return os.path.join(
        expanduser("~") + "/.pypads/" + run.info.experiment_id + "/" + run.info.run_id + "/" + file_name)


# --- Clean tmp files after run ---
original_end = mlflow.end_run


def end_run(*args, **kwargs):
    folder = to_folder("")
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


def try_write_artifact(file_name, obj, write_format):
    """
    Function to write an artifact to disk. TODO
    :param write_format:
    :param file_name:
    :param obj:
    :return:
    """
    path = to_folder(file_name)

    # Todo allow for configuring output format
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    # Functions for the options to write to
    def write_text(p, o):
        with open(p + ".txt", "w+") as fd:
            fd.write(to_string(o))
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

    # Log artifact to mlflow
    try_mlflow_log(mlflow.log_artifact, path)
