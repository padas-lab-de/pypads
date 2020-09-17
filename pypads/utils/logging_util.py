import json
import os
import pickle
from enum import Enum

import yaml

from pypads import logger


def get_temp_folder(run=None):
    """
    Get the base folder to log tmp files to. For now it can't be changed. Todo make configurable
    :return:
    """
    from pypads.app.pypads import get_current_pads
    pads = get_current_pads()
    run = run if run else pads.api.active_run()
    if run is None:
        raise ValueError("No active run is defined.")
    return os.path.join(pads.folder, "tmp", run.info.experiment_id, run.info.run_id) + os.path.sep


def get_by_value_in_enum(value, enum):
    for k, v in enum.__members__.items():
        if v.value == value:
            return v
    return None


class FileFormats(Enum):
    pickle = 'pickle'
    text = 'txt'
    yaml = 'yaml'
    json = 'json'
    unknown = ''


def find_file_format(file_name):
    name_split = file_name.rsplit(".", 1)
    if len(name_split) == 2:
        enum = get_by_value_in_enum(name_split[1], FileFormats)
        if enum:
            return enum
    return FileFormats.unknown


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


def write_yaml(p, o):
    try:
        with open(p + ".yaml", "w+") as fd:
            if isinstance(o, str):
                fd.write(o)
                # TODO check if valid yaml?
            else:
                yaml.dump(o, fd)
            return fd.name
    except Exception as e:
        logger.warning("Couldn't write meta as yaml. Trying to save it as json instead. " + str(e))
        return write_json(p, o)


def write_json(p, o):
    try:
        with open(p + ".json", "w+") as fd:
            if isinstance(o, str):
                fd.write(o)
                # TODO check if valid json?
            else:
                json.dump(o, fd)
            return fd.name
    except Exception as e:
        logger.warning("Couldn't write meta as json. Trying to save it as text instead. " + str(e))
        return write_text(p, o)


def read_text(p):
    with open(p, "r") as fd:
        return fd.read()


def read_pickle(p):
    try:
        with open(p, "rb") as fd:
            return pickle.load(fd)
    except Exception as e:
        logger.warning("Couldn't read pickle file. " + str(e))


def read_yaml(p):
    try:
        with open(p, "r") as fd:
            return yaml.full_load(fd)
    except Exception as e:
        logger.warning("Couldn't read artifact as yaml. Trying to read it as text instead. " + str(e))
        return read_text(p)


def read_json(p):
    try:
        with open(p, "r") as fd:
            return json.load(fd)
    except Exception as e:
        logger.warning("Couldn't read artifact as json. Trying to read it as text instead. " + str(e))
        return read_text(p)


writers = {
    FileFormats.pickle: write_pickle,
    FileFormats.text: write_text,
    FileFormats.yaml: write_yaml,
    FileFormats.json: write_json
}

readers = {
    FileFormats.pickle: read_pickle,
    FileFormats.text: read_text,
    FileFormats.yaml: read_yaml,
    FileFormats.json: read_json
}


def store_tmp_artifact(file_name, obj, write_format: FileFormats):
    """
    Temporarily stores artifact to disk to enable upload etc.
    :param file_name: Name for the file
    :param obj: Object in memory to store to disk
    :param write_format: Format to store the object in
    :return: Path to the temporarily stored artifact
    """
    from pypads.app.pypads import get_current_pads
    pads = get_current_pads()

    def tmp_cleanup(*args, **kwargs):
        import shutil
        from pypads.app.pypads import get_current_pads
        if get_current_pads():
            if os.path.isdir(get_temp_folder()):
                shutil.rmtree(get_temp_folder())

    pads.api.register_cleanup_fn("tmp_cleanup", tmp_cleanup)

    base_path = get_temp_folder()
    path = os.path.join(base_path, file_name)

    # Create dir in temporary_folder
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    # Write to disk
    if isinstance(write_format, str):
        if FileFormats[write_format]:
            write_format = FileFormats[write_format]
        else:
            logger.warning("Configured write format " + write_format + " not supported! ")
            return

    return writers[write_format](path, obj)


def read_artifact(path, read_format: FileFormats = None):
    if read_format is None:
        file_extension = path.split('.')[-1]
        read_format = get_by_value_in_enum(file_extension)
        if not read_format:
            logger.warning("Configured read format " + read_format + " not supported! ")
            return
    try:
        data = readers[read_format](path)
    except Exception as e:
        logger.warning("Reading artifact failed for '" + path + "'. " + str(e))
        data = "Cannot view content"
    return data


def _to_artifact_meta_name(name):
    return name + ".artifact"


def _to_metric_meta_name(name):
    return name + ".metric"


def _to_param_meta_name(name):
    return name + ".param"


def _to_tag_meta_name(name):
    return name + ".tag"
