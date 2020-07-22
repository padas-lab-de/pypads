import os
from typing import List, Type

from pydantic import BaseModel, HttpUrl

from pypads.app.injections.base_logger import LoggerCall, TrackedObject
from pypads.app.injections.injection import InjectionLoggerFunction
from pypads.model.models import InjectionLoggerCallModel, ArtifactMetaModel, TrackedObjectModel
from pypads.utils.logging_util import WriteFormats
from pypads.utils.util import local_uri_to_path, sizeof_fmt


def _get_cpu_usage():
    import psutil
    """
    cpu_usage = "CPU usage for cores:"
    for i, percentage in enumerate(psutil.cpu_percent(percpu=True)):
        cpu_usage += f"\nCore {i}: {percentage}%"
    cpu_usage += f"\nTotal CPU usage: {psutil.cpu_percent()}%"
    """
    cpu_usage = []
    for i, percentage in enumerate(psutil.cpu_percent(percpu=True)):
        cpu_usage.append(percentage)
    cpu_usage.append(psutil.cpu_percent())
    return cpu_usage


class CpuTO(TrackedObject):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    class CPUModel(TrackedObjectModel):
        uri: HttpUrl = "https://www.padre-lab.eu/onto/CpuData"

        class ParamModel(BaseModel):
            content_format: WriteFormats = WriteFormats.text
            name: str = ...
            type: str = ...
            usage: float = ...

            class Config:
                orm_mode = True

        input: List[ParamModel] = []

        class Config:
            orm_mode = True

        def to_string(_input):
            memory_usage = "CPU usage:"
            for item in _input[:-1]:
                memory_usage += f"\n\t{item.name}"
                memory_usage += f"\n\t\tusage: {item.usage}%"
            memory_usage += f"\n\tTotal CPU Usage: {_input[-1].usage}%"
            return memory_usage

        def json(_input):
            output = []
            for item in _input:
                output.append(item.json())
            return output

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.CPUModel

    def __init__(self, *args, call: LoggerCall, **kwargs):
        super().__init__(*args, original_call=call, **kwargs)

    def add_arg(self, name, cores, _format, type=0):
        path = os.path.join(self._base_path(), self._get_artifact_path(name))
        for idx, usage in enumerate(cores[:-1]):
            self.input.append(self.CPUModel.ParamModel(content_format=_format, name='Core:' + str(idx),
                                                       type=type, usage=usage))
        self.input.append(self.CPUModel.ParamModel(content_format=_format, name='Total Usage:',
                                                   type=type, usage=cores[-1]))
        _format = WriteFormats.json
        if _format == WriteFormats.text:
            _info = self.CPUModel.to_string(self.input)
        elif _format == WriteFormats.json:
            _info = self.CPUModel.json(self.input)
        else:
            _info = cores
        self._store_artifact(_info, ArtifactMetaModel(path=path,
                                                      description="CPU usage",
                                                      format=_format))

    def _get_artifact_path(self, name):
        return os.path.join(self.call.original_call.to_folder(), "cpu_usage", name)


class Cpu(InjectionLoggerFunction):
    """
    This function only writes an information of a constructor execution to the stdout.
    """
    name = "CPULogger"
    uri = "https://www.padre-lab.eu/onto/cpu-logger"

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


class RamTO(TrackedObject):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    class RAMModel(TrackedObjectModel):
        uri: HttpUrl = "https://www.padre-lab.eu/onto/RamData"

        class ParamModel(BaseModel):
            content_format: WriteFormats = WriteFormats.json
            used: int = ...
            free: int = ...
            percent: int = ...
            name: str = ...

            class Config:
                orm_mode = True
                arbitrary_types_allowed = True

        input: List[ParamModel] = []
        original_call: InjectionLoggerCallModel = ...

        class Config:
            orm_mode = True

        def to_string(_input):
            memory_usage = "Memory usage:"
            for item in _input:
                memory_usage += f"\n\tType:{item.name}"
                memory_usage += f"\n\t\tUsed:{sizeof_fmt(item.used)}"
                memory_usage += f"\n\t\tUsed:{sizeof_fmt(item.free)}"
                memory_usage += f"\n\t\tPercentage:{item.percent}%"
            return memory_usage

        def json(_input):
            output = []
            for item in _input:
                output.append(item.json())
            return output

    def __init__(self, *args, call: LoggerCall, **kwargs):
        super().__init__(*args, original_call=call, **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.RAMModel

    def add_arg(self, name, ram_info, swap_info, format, type=0):

        used = ram_info.get('used')
        free = ram_info.get('free')
        percent = ram_info.get('percent')
        self.input.append(self.RAMModel.ParamModel(content_format=format, name='ram_usage',
                                                   used=used, free=free, percent=percent, type=type))

        used = swap_info.get('used')
        free = swap_info.get('free')
        percent = swap_info.get('percent')
        self.input.append(self.RAMModel.ParamModel(content_format=format, name='swap_usage',
                                                   used=used, free=free, percent=percent, type=type))
        merged_dict = dict()
        merged_dict['RAM'] = ram_info
        merged_dict['swap'] = swap_info
        self.persist_arg(name, merged_dict, format)

    def persist_arg(self, name, memory_info, _format):
        # TODO try to extract parameter documentation?
        path = os.path.join(self._base_path(), self._get_artifact_path(name))

        if _format == WriteFormats.text:
            _info = self.RAMModel.to_string(self.input)
        elif _format == WriteFormats.json:
            _info = self.RAMModel.json(self.input)
        else:
            _info = memory_info

        self._store_artifact(_info, ArtifactMetaModel(path=path,
                                                      description="Memory Information",
                                                      format=_format))

    def _get_artifact_path(self, name):
        return os.path.join(self.call.original_call.to_folder(), "ram_usage", name)


class Ram(InjectionLoggerFunction):
    """
    This function only writes an information of a constructor execution to the stdout.
    """

    name = "RAMLogger"
    uri = "https://www.padre-lab.eu/onto/ram-logger"

    def tracking_object_schemata(self):
        return [RamTO.RAMModel.schema()]

    _dependencies = {"psutil"}

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.json, _logger_call: LoggerCall, _args, _kwargs, **kwargs):
        pre_ram_usage = RamTO(call=_logger_call)
        ram_info, swap_info = _get_memory_usage()
        pre_ram_usage.add_arg("pre_memory_usage", ram_info, swap_info, _pypads_write_format)

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


class DiskTO(TrackedObject):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    class DiskModel(TrackedObjectModel):
        uri: HttpUrl = "https://www.padre-lab.eu/onto/DiskData"

        class ParamModel(BaseModel):
            content_format: WriteFormats = WriteFormats.text
            name: str = ...
            type: str = ...
            device: str = ...
            file_system: str = ...
            mount_point: str = ...
            free: int = ...
            used: int = ...
            percent: float = ...

            class Config:
                orm_mode = True

        input: List[ParamModel] = []
        original_call: InjectionLoggerCallModel = ...

        class Config:
            orm_mode = True

        def to_string(_input):
            memory_usage = "Memory usage:"
            for item in _input:
                memory_usage += f"\n\tPartition Name: {item.name}"
                memory_usage += f"\n\t\tDevice: {item.device}"
                memory_usage += f"\n\t\tFile System: {item.file_system}"
                memory_usage += f"\n\t\tMount Point: {item.mount_point}"
                memory_usage += f"\n\t\tUsed: {sizeof_fmt(item.used)}"
                memory_usage += f"\n\t\tUsed: {sizeof_fmt(item.free)}"
                memory_usage += f"\n\t\tPercentage: {item.percent}%"
            return memory_usage

        def json(_input):
            output = []
            for item in _input:
                output.append(item.json())
            return output

    def __init__(self, *args, call: LoggerCall, **kwargs):
        super().__init__(*args, original_call=call, **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.DiskModel

    def add_arg(self, name, value, _format, type=0):
        # TODO try to extract parameter documentation?
        index = len(self.input)
        path = os.path.join(self._base_path(), self._get_artifact_path(name))

        _name = 'disk'
        file_system = 'disk'
        device = 'disk'
        mount_point = ''
        free = value.get('free')
        used = value.get('used')
        percent = value.get('percentage')

        self.input.append(self.DiskModel.ParamModel(content_format=_format, name=_name, file_system=file_system,
                          device=device, mount_point=mount_point, free=free, used=used, percent=percent, type=type))
        for partition, info in value.get('partitions', dict()).items():
            _name = partition
            file_system = info.get('FileSystem')
            device = info.get('device')
            mount_point = info.get('MountPoint')
            free = info.get('free')
            used = info.get('used')
            percent = info.get('percentage')
            self.input.append(self.DiskModel.ParamModel(content_format=_format, name=_name, file_system=file_system,
                              device=device, mount_point=mount_point, free=free, used=used, percent=percent, type=type))

        if _format == WriteFormats.text:
            _info = self.DiskModel.to_string(self.input)
        elif _format == WriteFormats.json:
            _info = self.DiskModel.json(self.input)
        else:
            _info = value
        self._store_artifact(_info, ArtifactMetaModel(path=path,
                                                      description="Disk usage",
                                                      format=_format))

    def _get_artifact_path(self, name):
        return os.path.join(self.call.original_call.to_folder(), "disk_usage", name)


class Disk(InjectionLoggerFunction):
    """
    This function only writes an information of a constructor execution to the stdout.
    """

    name = "DiskLogger"
    uri = "https://www.padre-lab.eu/onto/disk-logger"

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
    output_dict['free'] = disk_usage.free
    output_dict['used'] = disk_usage.used
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
