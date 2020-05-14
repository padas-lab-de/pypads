import os
import pickle
from enum import Enum

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads import logger


def get_temp_folder(run=None):
    """
    Get the base folder to log tmp files to. For now it can't be changed. Todo make configurable
    :return:
    """
    from pypads.pypads import get_current_pads
    pads = get_current_pads()
    run = run if run else pads.api.active_run()
    if run is None:
        raise ValueError("No active run is defined.")
    return os.path.join(pads.folder, "tmp", run.info.experiment_id, run.info.run_id) + os.path.sep


def get_run_folder():
    """
    Get the folder holding the run information.
    :return:
    """
    run = mlflow.active_run()
    if run is None:
        raise ValueError("No active run is defined.")
    # TODO use artifact download if needed or load artifact.
    return os.path.join(mlflow.get_tracking_uri(), run.info.experiment_id, run.info.run_id)


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
    # TODO make defensive
    base_path = get_run_folder()
    path = os.path.join(base_path, "artifacts", file_name)
    with open(path, "r") as meta:
        data = meta.readlines()
    return data


def try_write_artifact(file_name, obj, write_format, preserve_folder=True):
    """
    Function to write an artifact to disk.
    :param write_format:
    :param file_name:
    :param obj:
    :return:
    """
    base_path = get_temp_folder()
    path = os.path.join(base_path, file_name)

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
