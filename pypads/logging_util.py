import os
import pickle
import shutil
from enum import Enum
from os.path import expanduser

import mlflow
from loguru import logger
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


def get_run_folder():
    """
    Get the folder holding the run information.
    :return:
    """
    run = mlflow.active_run()
    if run is None:
        raise ValueError("No active run is defined.")
    # TODO use artifact download if needed or load artifact. Don't hardcode .mlflow
    return os.path.join(expanduser("~"), ".mlruns", run.info.experiment_id, run.info.run_id)


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


def try_read_artifact(file_name):
    # TODO defensive
    base_path = get_run_folder()
    path = os.path.join(base_path, "artifacts", file_name)
    with open(path, "r") as meta:
        data = meta.readlines()
    return data


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
            logger.warning("Couldn't pickle output. Trying to save toString instead. " + str(e))
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
            logger.warning("Configured write format " + write_format + " not supported! ")
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
