import json
import os
import pickle
from collections import defaultdict
from enum import Enum
from pathlib import PurePath
from types import GeneratorType
from typing import Any, Optional, Union, Set, Dict, Callable, Tuple, List

import yaml
from pydantic import BaseModel
from pydantic.json import ENCODERS_BY_TYPE

from pypads import logger
from pypads.utils.util import dict_merge


def merge_mapping_data(matched_mappings):
    return dict_merge(*[mm.mapping.values['data'] for mm in matched_mappings if "data" in mm.mapping.values],
                      str_to_set=True)


def data_str(data, *path, default=None, warning=None):
    entry = data_path(data, *path, default=default, warning=warning)
    if entry == default:
        return default
    if isinstance(entry, set):
        if len(entry) > 0:
            return iter(entry).__next__()
        else:
            return ""
    else:
        return entry


def data_path(data, *path, default=None, warning=None):
    """
    Gets an data item of given dict at path
    :param data:
    :param path:
    :param default:
    :param warning:
    :return:
    """
    cur = data
    for i, p in enumerate(path):
        if isinstance(cur, list):
            out = []
            for list_element in cur:
                value = data_path(list_element, *path[i:])
                if value is not None:
                    if isinstance(value, list) and not len(path[i:]) == 0:
                        out.extend(value)
                    else:
                        out.append(value)
            return out if len(out) > 0 else default
        elif p in cur:
            # If list recursively call itself
            # Multiple return values needed instead of one
            cur = cur[p]
        else:
            if warning is not None:
                logger.warning(warning)
            return default
    return cur


def add_data(data, *path, value):
    """
    Add an data item to the given dict
    :param data:
    :param path:
    :param value:
    :return:
    """
    cur = data
    for i, p in enumerate(path):
        if isinstance(cur, list):
            for list_element in cur:
                add_data(list_element, *path[i:], value=value)
        else:
            if i == len(path) - 1:
                if p not in cur:
                    cur[p] = value
                elif isinstance(cur[p], list):
                    if isinstance(value, list):
                        cur[p].extend(value)
                    else:
                        cur[p].append(value)
                else:
                    cur[p] = value
            else:
                if p not in cur:
                    cur[p] = {}
                cur = cur[p]
    return cur


def get_artifact_dir(obj):
    """
    Get a path to a given entry object.
    :param obj:
    :return:
    """
    model_cls = obj.get_model_cls()

    from pypads.model.models import RunObjectModel
    if issubclass(model_cls, RunObjectModel):
        from pypads.model.models import EntryModel
        obj: Union[RunObjectModel, EntryModel]
        return os.path.join(obj.experiment.uid, obj.run.uid, "artifacts", get_relative_artifact_dir(obj))

    raise Exception("Given object is not part of a run/experiment.")


def get_relative_artifact_dir(obj):
    """
    Get a relative path to a given entry object
    :param obj:
    :return:
    """
    from pypads.app.injections.tracked_object import ChildResultHolderMixin
    from pypads.model.models import EntryModel
    if isinstance(obj, ChildResultHolderMixin):
        obj: Union[EntryModel, ChildResultHolderMixin]
        return os.path.join(get_relative_artifact_dir(obj.parent), obj.category)

    from pypads.app.injections.tracked_object import ResultHolderMixin
    if isinstance(obj, ResultHolderMixin):
        obj: Union[EntryModel, ResultHolderMixin]
        return os.path.join(get_relative_artifact_dir(obj.producer), obj.category)

    return os.path.join(obj.category)


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


def write_unknown(p, o):
    with open(p, "w+") as fd:
        fd.write(str(o))
        return fd.name


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
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.warning("Couldn't read pickle file. " + str(e))


def read_yaml(p):
    try:
        with open(p, "r") as fd:
            return yaml.full_load(fd)
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.warning("Couldn't read artifact as yaml. Trying to read it as text instead. " + str(e))
        return read_text(p)


def read_json(p):
    try:
        with open(p, "r") as fd:
            return json.load(fd)
    except FileNotFoundError:
        return None
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

    pads.api.register_teardown_utility("tmp_cleanup", tmp_cleanup)

    base_path = get_temp_folder()
    path = os.path.join(base_path, file_name)

    # Create dir in temporary_folder
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    # Write to disk
    if isinstance(write_format, str):
        if write_format in FileFormats.__members__:
            write_format = FileFormats[write_format]
        else:
            logger.warning("Configured write format " + write_format + " not directly supported!")
            return write_unknown(f"{path}.{write_format}", obj)

    return writers[write_format](path, obj)


def read_artifact(path, read_format: FileFormats = None):
    if read_format is None:
        file_extension = path.split('.')[-1]
        read_format = get_by_value_in_enum(file_extension, FileFormats)
        if not read_format:
            logger.warning("Configured read format " + read_format + " not supported! ")
            return
    try:
        data = readers[read_format](path)
    except Exception as e:
        data = None
    return data


# FastAPI
SetIntStr = Set[Union[int, str]]
DictIntStrAny = Dict[Union[int, str], Any]


def generate_encoders_by_class_tuples(
        type_encoder_map: Dict[Any, Callable]
) -> Dict[Callable, Tuple]:
    encoders_by_class_tuples: Dict[Callable, Tuple] = defaultdict(tuple)
    for type_, encoder in type_encoder_map.items():
        encoders_by_class_tuples[encoder] += (type_,)
    return encoders_by_class_tuples


encoders_by_class_tuples = generate_encoders_by_class_tuples(ENCODERS_BY_TYPE)


def jsonable_encoder(
        obj: Any,
        include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
        exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        custom_encoder: dict = {},
        sqlalchemy_safe: bool = True,
) -> Any:
    if include is not None and not isinstance(include, set):
        include = set(include)
    if exclude is not None and not isinstance(exclude, set):
        exclude = set(exclude)
    if isinstance(obj, BaseModel):
        encoder = getattr(obj.__config__, "json_encoders", {})
        if custom_encoder:
            encoder.update(custom_encoder)
        obj_dict = obj.dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
        )
        if "__root__" in obj_dict:
            obj_dict = obj_dict["__root__"]
        return jsonable_encoder(
            obj_dict,
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
            custom_encoder=encoder,
            sqlalchemy_safe=sqlalchemy_safe,
        )
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, PurePath):
        return str(obj)
    if isinstance(obj, (str, int, float, type(None))):
        return obj
    if isinstance(obj, dict):
        encoded_dict = {}
        for key, value in obj.items():
            if (
                    (
                            not sqlalchemy_safe
                            or (not isinstance(key, str))
                            or (not key.startswith("_sa"))
                    )
                    and (value is not None or not exclude_none)
                    and ((include and key in include) or not exclude or key not in exclude)
            ):
                encoded_key = jsonable_encoder(
                    key,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_none=exclude_none,
                    custom_encoder=custom_encoder,
                    sqlalchemy_safe=sqlalchemy_safe,
                )
                encoded_value = jsonable_encoder(
                    value,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_none=exclude_none,
                    custom_encoder=custom_encoder,
                    sqlalchemy_safe=sqlalchemy_safe,
                )
                encoded_dict[encoded_key] = encoded_value
        return encoded_dict
    if isinstance(obj, (list, set, frozenset, GeneratorType, tuple)):
        encoded_list = []
        for item in obj:
            encoded_list.append(
                jsonable_encoder(
                    item,
                    include=include,
                    exclude=exclude,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                    custom_encoder=custom_encoder,
                    sqlalchemy_safe=sqlalchemy_safe,
                )
            )
        return encoded_list

    if custom_encoder:
        if type(obj) in custom_encoder:
            return custom_encoder[type(obj)](obj)
        else:
            for encoder_type, encoder in custom_encoder.items():
                if isinstance(obj, encoder_type):
                    return encoder(obj)

    if type(obj) in ENCODERS_BY_TYPE:
        return ENCODERS_BY_TYPE[type(obj)](obj)
    for encoder, classes_tuple in encoders_by_class_tuples.items():
        if isinstance(obj, classes_tuple):
            return encoder(obj)

    errors: List[Exception] = []
    try:
        data = dict(obj)
    except Exception as e:
        errors.append(e)
        try:
            data = vars(obj)
        except Exception as e:
            errors.append(e)
            raise ValueError(errors)
    return jsonable_encoder(
        data,
        by_alias=by_alias,
        exclude_unset=exclude_unset,
        exclude_defaults=exclude_defaults,
        exclude_none=exclude_none,
        custom_encoder=custom_encoder,
        sqlalchemy_safe=sqlalchemy_safe,
    )
