import os
from typing import List, Type

from pydantic import BaseModel, HttpUrl

from pypads.app.injections.base_logger import LoggerCall, TrackedObject
from pypads.app.injections.injection import InjectionLogger
from pypads.model.models import ArtifactMetaModel, TrackedObjectModel, OutputModel
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

        class CpuCoreModel(BaseModel):
            name: str = ...
            usage: float = ...

            class Config:
                orm_mode = True

        content_format: WriteFormats = WriteFormats.text
        cpu_cores: List[CpuCoreModel] = []
        total_usage: str = ...

        class Config:
            orm_mode = True
            arbitrary_types_allowed = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.CPUModel

    def __init__(self, *args, tracked_by: LoggerCall, **kwargs):
        super().__init__(*args, tracked_by=tracked_by, **kwargs)

    def to_string(self):
        cpu_usage = "CPU usage:"
        for item in self.cpu_cores[:-1]:
            cpu_usage += f"\n\t{item.name}"
            cpu_usage += f"\n\t\tusage: {item.usage}%"
        cpu_usage += f"\n\tTotal CPU Usage: {self.total_usage}%"
        return cpu_usage

    def add_cpu_usage(self, name, cores):
        path = os.path.join(self._base_path(), self._get_artifact_path(name))
        for idx, usage in enumerate(cores[:-1]):
            self.cpu_cores.append(self.CPUModel.CpuCoreModel(name='Core:' + str(idx),
                                                             usage=usage))
        self.total_usage = cores[-1]

        _format = self.content_format
        if _format == WriteFormats.text:
            _info = self.to_string()
        elif _format == WriteFormats.json:
            _info = self.json()
        else:
            _info = cores
        self._store_artifact(_info, ArtifactMetaModel(path=path,
                                                      description="CPU usage",
                                                      format=_format))

    def _get_artifact_path(self, name):
        return os.path.join(str(id(self)), "cpu_usage", name)


class CpuILF(InjectionLogger):
    """This logger extracts the cpu information of your machine."""
    name = "CPULogger"
    uri = "https://www.padre-lab.eu/onto/cpu-logger"

    class CpuILFOutput(OutputModel):
        is_a: HttpUrl = "https://www.padre-lab.eu/onto/CpuILF-Output"

        pre_cpu_usage: CpuTO.get_model_cls() = ...
        post_cpu_usage: CpuTO.get_model_cls() = ...

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.CpuILFOutput

    _dependencies = {"psutil"}

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.text, _logger_call: LoggerCall, _logger_output,
                _args, _kwargs,
                **kwargs):
        cpu_usage = CpuTO(tracked_by=_logger_call, content_format=_pypads_write_format)
        cpu_usage.add_cpu_usage("pre_cpu_usage", _get_cpu_usage())

        cpu_usage.store(_logger_output, key="pre_cpu_usage")

    # def __call_wrapped__(self, ctx, *args, _pypads_env, _args, _kwargs, **_pypads_hook_params):
    #     # TODO track while executing instead of before and after
    #     return super().__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=_args, _kwargs=_kwargs,
    #                                     **_pypads_hook_params)

    def __post__(self, ctx, *args, _pypads_write_format=WriteFormats.text, _logger_call, _logger_output, _pypads_result,
                 **kwargs):
        cpu_usage = CpuTO(tracked_by=_logger_call, content_format=_pypads_write_format)
        cpu_usage.add_cpu_usage("post_cpu_usage", _get_cpu_usage())

        cpu_usage.store(_logger_output, key="post_cpu_usage")


class RamTO(TrackedObject):
    """
    Function logging the memory information of the current pipeline object function call.
    """

    class RAMModel(TrackedObjectModel):
        uri: HttpUrl = "https://www.padre-lab.eu/onto/RamData"

        class MemoryModel(BaseModel):
            used: int = ...
            free: int = ...
            percentage: float = ...
            type: str = ...

        content_format: WriteFormats = WriteFormats.json
        virtual_memory: MemoryModel = None
        swap_memory: MemoryModel = None

        class Config:
            orm_mode = True
            arbitrary_types_allowed = True

    def __init__(self, *args, tracked_by: LoggerCall, **kwargs):
        super().__init__(*args, tracked_by=tracked_by, **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.RAMModel

    def to_string(self):
        memory_usage = "Memory usage:"
        for item in [self.virtual_memory, self.swap_memory]:
            memory_usage += f"\n\tType:{item.type}"
            memory_usage += f"\n\t\tUsed:{sizeof_fmt(item.used)}"
            memory_usage += f"\n\t\tUsed:{sizeof_fmt(item.free)}"
            memory_usage += f"\n\t\tPercentage:{item.percentage}%"
        return memory_usage

    def add_memory_usage(self, name, ram_info, swap_info):

        used = ram_info.get('used')
        free = ram_info.get('free')
        percent = ram_info.get('percent')
        self.virtual_memory = self.RAMModel.MemoryModel(name='ram_usage',
                                                        used=used, free=free, percentage=percent, type="RAM")

        used = swap_info.get('used')
        free = swap_info.get('free')
        percent = swap_info.get('percent')
        self.swap_memory = self.RAMModel.MemoryModel(name='swap_usage',
                                                     used=used, free=free, percentage=percent, type="Swap")

        merged_dict = dict()
        merged_dict['RAM'] = ram_info
        merged_dict['swap'] = swap_info
        self.persist_memory_info(name, merged_dict)

    def persist_memory_info(self, name, memory_info):
        # TODO try to extract parameter documentation?
        path = os.path.join(self._base_path(), self._get_artifact_path(name))

        if self.content_format == WriteFormats.text:
            _info = self.to_string()
        elif self.content_format == WriteFormats.json:
            _info = self.json()
        else:
            _info = memory_info

        self._store_artifact(_info, ArtifactMetaModel(path=path,
                                                      description="Memory Information",
                                                      format=self.content_format))

    def _get_artifact_path(self, name):
        return os.path.join(str(id(self)), "memory_usage", name)


class RamILF(InjectionLogger):
    """
    This function only writes an information of a constructor execution to the stdout.
    """

    name = "RAMLogger"
    uri = "https://www.padre-lab.eu/onto/ram-logger"

    class RamILFOutput(OutputModel):
        is_a: HttpUrl = "https://www.padre-lab.eu/onto/RamILF-Output"

        pre_memory_usage: RamTO.get_model_cls() = ...
        post_memory_usage: RamTO.get_model_cls() = ...

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.RamILFOutput

    _dependencies = {"psutil"}

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.json, _logger_call: LoggerCall, _logger_output,
                _args, _kwargs, **kwargs):
        memory_usage = RamTO(tracked_by=_logger_call, content_format=_pypads_write_format)

        ram_info, swap_info = _get_memory_usage()
        memory_usage.add_memory_usage("pre_memory_usage", ram_info, swap_info)

        memory_usage.store(_logger_output, key="pre_memory_usage")

    # def __call_wrapped__(self, ctx, *args, _pypads_env, _args, _kwargs, **_pypads_hook_params):
    #     # TODO track while executing instead of before and after
    #     return super().__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=_args, _kwargs=_kwargs)

    def __post__(self, ctx, *args, _pypads_write_format=WriteFormats.json, _logger_call, _logger_output, _pypads_result,
                 **kwargs):
        memory_usage = RamTO(tracked_by=_logger_call, content_format=_pypads_write_format)

        ram_info, swap_info = _get_memory_usage()
        memory_usage.add_memory_usage("post_memory_usage", ram_info, swap_info)

        memory_usage.store(_logger_output, key="post_memory_usage")


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

        class PartitionModel(BaseModel):
            name: str = ...
            device: str = ...
            file_system: str = ...
            mount_point: str = ...
            free: int = ...
            used: int = ...
            percentage: float = ...

            class Config:
                orm_mode = True

        content_format: WriteFormats = WriteFormats.text
        partitions: List[PartitionModel] = []

        folder: str = ...
        total_free_space: int = ...
        total_used_space: int = ...
        total_percentage: float = ...

        class Config:
            orm_mode = True
            arbitrary_types_allowed = True

    def __init__(self, *args, tracked_by: LoggerCall, **kwargs):
        super().__init__(*args, tracked_by=tracked_by, **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.DiskModel

    def to_string(self):
        memory_usage = "Memory usage:"
        for item in self.partitions:
            memory_usage += f"\n\tPartition Name: {item.name}"
            memory_usage += f"\n\t\tDevice: {item.device}"
            memory_usage += f"\n\t\tFile System: {item.file_system}"
            memory_usage += f"\n\t\tMount Point: {item.mount_point}"
            memory_usage += f"\n\t\tUsed: {sizeof_fmt(item.used)}"
            memory_usage += f"\n\t\tFree: {sizeof_fmt(item.free)}"
            memory_usage += f"\n\t\tPercentage: {item.percentage}%"
        memory_usage += f"\n\tTotal Used Space: {self.total_used_space}%"
        memory_usage += f"\n\tTotal Free Space: {self.total_free_space}%"
        memory_usage += f"\n\tTotal Percentage: {self.total_percentage}%"
        return memory_usage

    def add_disk_usage(self, name, value):
        # TODO try to extract parameter documentation?
        path = os.path.join(self._base_path(), self._get_artifact_path(name))

        self.total_free_space = value.get('free')
        self.total_used_space = value.get('used')
        self.total_percentage = value.get('percentage')

        for partition, info in value.get('partitions', dict()).items():
            _name = partition
            file_system = info.get('FileSystem')
            device = info.get('device')
            mount_point = info.get('MountPoint')
            free = info.get('free')
            used = info.get('used')
            percent = info.get('percentage')
            self.partitions.append(self.DiskModel.PartitionModel(name=_name, file_system=file_system,
                                                                 device=device, mount_point=mount_point, free=free,
                                                                 used=used,
                                                                 percentage=percent))
        _format = self.content_format
        if _format == WriteFormats.text:
            _info = self.to_string()
        elif _format == WriteFormats.json:
            _info = self.json()
        else:
            _info = value
        self._store_artifact(_info, ArtifactMetaModel(path=path,
                                                      description="Disk usage",
                                                      format=_format))

    def _get_artifact_path(self, name):
        return os.path.join(str(id(self)), "disk_usage", name)


class DiskILF(InjectionLogger):
    """
    This function only writes an information of a constructor execution to the stdout.
    """

    name = "DiskLogger"
    uri = "https://www.padre-lab.eu/onto/disk-logger"

    class DiskILFOutput(OutputModel):
        is_a: HttpUrl = "https://www.padre-lab.eu/onto/DiskILF-Output"

        pre_disk_usage: DiskTO.get_model_cls() = ...
        post_disk_usage: DiskTO.get_model_cls() = ...

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.DiskILFOutput

    @classmethod
    def _needed_packages(cls):
        return ["psutil"]

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.text, _logger_call: LoggerCall, _logger_output, _args, _kwargs,
                **kwargs):
        from pypads.app.base import PyPads
        from pypads.app.pypads import get_current_pads
        pads: PyPads = get_current_pads()
        path = local_uri_to_path(pads.uri)

        disk_usage = DiskTO(tracked_by=_logger_call, content_format=_pypads_write_format, folder=path)
        disk_usage.add_disk_usage("pre_disk_usage", _get_disk_usage(path))

        disk_usage.store(_logger_output, key="pre_disk_usage")

    # def __call_wrapped__(self, ctx, *args, _pypads_env, _args, _kwargs, **_pypads_hook_params):
    #     # TODO track while executing instead of before and after
    #     return super().__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=_args, _kwargs=_kwargs,
    #                                     **_pypads_hook_params)

    def __post__(self, ctx, *args, _pypads_write_format=WriteFormats.text, _logger_call, _logger_output, _pypads_result, **kwargs):
        from pypads.app.base import PyPads
        from pypads.app.pypads import get_current_pads
        pads: PyPads = get_current_pads()
        path = local_uri_to_path(pads.uri)

        disk_usage = DiskTO(tracked_by=_logger_call, content_format=_pypads_write_format, folder=path)
        disk_usage.add_disk_usage("post_disk_usage", _get_disk_usage(path))

        disk_usage.store(_logger_output, key="post_disk_usage")


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
