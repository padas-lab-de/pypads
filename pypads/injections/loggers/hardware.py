import os
from typing import List

from pydantic import BaseModel

from pypads.app.injections.base_logger import LoggingFunction, LoggerCall, LoggerTrackingObject
from pypads.model.models import LoggerCallModel, ArtifactMetaModel
from pypads.utils.logging_util import try_write_artifact, WriteFormats
from pypads.utils.util import local_uri_to_path, sizeof_fmt


def _get_cpu_usage():
    import psutil
    cpu_usage = "CPU usage for cores:"
    for i, percentage in enumerate(psutil.cpu_percent(percpu=True)):
        cpu_usage += f"\nCore {i}: {percentage}%"
    cpu_usage += f"\nTotal CPU usage: {psutil.cpu_percent()}%"

    return cpu_usage


class CpuTO(LoggerTrackingObject):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    class CPUModel(BaseModel):
        class ParamModel(BaseModel):
            content_format: WriteFormats = WriteFormats.text
            name: str = ...
            value: str = ...  # path to the artifact containing the param
            type: str = ...

            class Config:
                orm_mode = True

        input: List[ParamModel] = []
        call: LoggerCallModel = ...

        class Config:
            orm_mode = True

    def __init__(self, *args, call: LoggerCall, **kwargs):
        super().__init__(*args, model_cls=self.CPUModel, call=call, **kwargs)

    def add_arg(self, name, value, format, type=0):
        path = os.path.join(self._base_path(), self._get_artifact_path(name))
        self.input.append(self.CPUModel.ParamModel(content_format=format, name=name, value=path, type=type))
        self._store_artifact(value, ArtifactMetaModel(path=path,
                                                      description="CPU usage",
                                                      format=format))

    def _get_artifact_path(self, name):
        return os.path.join(self.call.call.to_folder(), "cpu_usage", name)


class Cpu(LoggingFunction):
    """
    This function only writes an information of a constructor execution to the stdout.
    """
    name = "CPULogger"
    url = "https://www.padre-lab.eu/onto/cpu-logger"

    def tracking_object_schemata(self):
        return [CpuTO.CPUModel.schema()]

    _dependencies = {"psutil"}

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.text, _logger_call: LoggerCall, _args, _kwargs, **kwargs):

        inputs = CpuTO(call=_logger_call)
        inputs.add_arg("pre_cpu_usage", _get_cpu_usage(), _pypads_write_format)

    def __call_wrapped__(self, ctx, *args, _pypads_env, _args, _kwargs, **_pypads_hook_params):
        # TODO track while executing instead of before and after
        return super().__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=_args, _kwargs=_kwargs,
                                        **_pypads_hook_params)

    def __post__(self, ctx, *args, _pypads_write_format=WriteFormats.text, _logger_call, _pypads_result, **kwargs):
        output = CpuTO(call=_logger_call)
        output.add_arg("post_cpu_usage", _get_cpu_usage(), _pypads_write_format)


class RamTO(LoggerTrackingObject):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    class RAMModel(BaseModel):
        class ParamModel(BaseModel):
            content_format: WriteFormats = WriteFormats.json
            ram_dict: dict = ...
            swap_dict: dict = ...
            name: str = ...

            class Config:
                orm_mode = True
                arbitrary_types_allowed = True

        input: List[ParamModel] = []
        call: LoggerCallModel = ...

        class Config:
            orm_mode = True

    def __init__(self, *args, call: LoggerCall, **kwargs):
        super().__init__(*args, model_cls=self.RAMModel, call=call, **kwargs)

    def add_arg(self, name, ram_info, swap_info, format, type=0):
        self.input.append(self.RAMModel.ParamModel(content_format=format, name=name,
                                                   ram_dict=ram_info, swap_dict=swap_info, type=type))
        merged_dict = dict()
        merged_dict['RAM'] = ram_info
        merged_dict['swap'] = swap_info
        self.persist_arg(name, merged_dict, format)

    def persist_arg(self, name, memory_info, format):
        # TODO try to extract parameter documentation?
        index = len(self.input)
        path = os.path.join(self._base_path(), self._get_artifact_path(name))

        if format == WriteFormats.text:
            _info = self.to_string(memory_info)
        else:
            _info = memory_info

        self._store_artifact(_info, ArtifactMetaModel(path=path,
                                                         description="Memory Information",
                                                         format=format))

    def _get_artifact_path(self, name):
        return os.path.join(self.call.call.to_folder(), "ram_usage", name)

    def to_string(self, memory_dict):
        memory_usage = "Memory usage:"
        memory_usage += f"\n\tUsed:{sizeof_fmt(memory_dict.get('RAM', dict()).get('used', 0.0))}"
        memory_usage += f"\n\tPercentage:{memory_dict.get('RAM', dict()).get('percent',0.0)}%"
        memory_usage += f"\nSwap usage::"
        memory_usage += f"\n\tFree:{sizeof_fmt(memory_dict.get('swap', dict()).get('free', 0.0))}"
        memory_usage += f"\n\tUsed:{sizeof_fmt(memory_dict.get('swap', dict()).get('used', 0.0))}"
        memory_usage += f"\n\tPercentage:{memory_dict.get('swap', dict()).get('percent', 0.0)}%"
        return memory_usage


class Ram(LoggingFunction):
    """
    This function only writes an information of a constructor execution to the stdout.
    """

    name = "RAMLogger"
    url = "https://www.padre-lab.eu/onto/ram-logger"

    def tracking_object_schemata(self):
        return [RamTO.RAMModel.schema()]

    _dependencies = {"psutil"}

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.json, _logger_call: LoggerCall, _args, _kwargs, **kwargs):
        pre_ram_usage = RamTO(call=_logger_call)
        ram_info, swap_info = _get_memory_usage()
        pre_ram_usage.add_arg("pre_memory_usage", ram_info, swap_info, WriteFormats.text)

    def __call_wrapped__(self, ctx, *args, _pypads_env, _args, _kwargs, **_pypads_hook_params):
        # TODO track while executing instead of before and after
        return super().__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=_args, _kwargs=_kwargs,
                                        **_pypads_hook_params)

    def __post__(self, ctx, *args, _pypads_write_format=WriteFormats.json, _logger_call, _pypads_result, **kwargs):
        post_ram_usage = RamTO(call=_logger_call)
        ram_info, swap_info = _get_memory_usage()
        post_ram_usage.add_arg("post_memory_usage", ram_info, swap_info, _pypads_write_format)


def _get_memory_usage():
    import psutil
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return dict(memory._asdict()), dict(swap._asdict())


class DiskTO(LoggerTrackingObject):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    class DiskModel(BaseModel):
        class ParamModel(BaseModel):
            content_format: WriteFormats = WriteFormats.text
            name: str = ...
            value: str = ...  # path to the artifact containing the param
            type: str = ...

            class Config:
                orm_mode = True

        input: List[ParamModel] = []
        call: LoggerCallModel = ...

        class Config:
            orm_mode = True

    def __init__(self, *args, call: LoggerCall, **kwargs):
        super().__init__(*args, model_cls=self.DiskModel, call=call, **kwargs)

    def add_arg(self, name, value, _format, type=0):
        # TODO try to extract parameter documentation?
        index = len(self.input)
        path = os.path.join(self._base_path(), self._get_artifact_path(name))
        self.input.append(self.DiskModel.ParamModel(content_format=_format, name=name, value=path, type=type))
        self._store_artifact(value, ArtifactMetaModel(path=path,
                                                      description="Disk usage",
                                                      format=_format))

    def _get_artifact_path(self, name):
        return os.path.join(self.call.call.to_folder(), "disk_usage", name)


class Disk(LoggingFunction):
    """
    This function only writes an information of a constructor execution to the stdout.
    """

    name = "DiskLogger"
    url = "https://www.padre-lab.eu/onto/disk-logger"

    def tracking_object_schemata(self):
        return [DiskTO.DiskModel.schema()]

    @classmethod
    def _needed_packages(cls):
        return ["psutil"]

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.text, _logger_call: LoggerCall, _args, _kwargs, **kwargs):
        from pypads.app.base import PyPads
        from pypads.app.pypads import get_current_pads
        pads: PyPads = get_current_pads()
        path = local_uri_to_path(pads.uri)
        inputs = DiskTO(call=_logger_call)
        inputs.add_arg("pre_disk_usage", _get_disk_usage(path), _pypads_write_format)

    def __call_wrapped__(self, ctx, *args, _pypads_env, _args, _kwargs, **_pypads_hook_params):
        # TODO track while executing instead of before and after
        return super().__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=_args, _kwargs=_kwargs,
                                        **_pypads_hook_params)

    def __post__(self, ctx, *args, _pypads_write_format=WriteFormats.text, _logger_call, _pypads_result, **kwargs):
        from pypads.app.base import PyPads
        from pypads.app.pypads import get_current_pads
        pads: PyPads = get_current_pads()
        path = local_uri_to_path(pads.uri)
        inputs = DiskTO(call=_logger_call)
        inputs.add_arg("post_disk_usage", _get_disk_usage(path), _pypads_write_format)


def _get_disk_usage(path):
    import psutil
    # See https://www.thepythoncode.com/article/get-hardware-system-information-python
    disk_usage = psutil.disk_usage(path)
    output_dict = dict()
    output_dict['free'] = sizeof_fmt(disk_usage.free)
    output_dict['used'] = sizeof_fmt(disk_usage.used)
    output_dict['percentage'] = disk_usage.percent

    partition_dict = dict()
    partitions = psutil.disk_partitions()
    for idx, partition in enumerate(partitions):
        temp_dict = dict()
        temp_dict['device'] = partition.device
        temp_dict['MountPoint'] = partition.mountpoint
        temp_dict['FileSystem'] = partition.fstype
        partition_usage = None
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            # output_ += f"\n\t\t Busy!"
            continue

        temp_dict['free'] = partition_usage.free
        temp_dict['used'] = partition_usage.used
        temp_dict['percentage'] = partition_usage.percent

        partition_dict['partition' + str(idx)] = temp_dict

    output_dict['partitions'] = partition_dict
    return output_dict
