import os
from typing import List, Type

from pydantic import BaseModel, HttpUrl

from pypads.app.injections.base_logger import LoggerCall, TrackedObject
from pypads.app.injections.injection import InjectionLogger
from pypads.model.models import TrackedObjectModel, OutputModel
from pypads.utils.logging_util import WriteFormats
from pypads.utils.util import local_uri_to_path, sizeof_fmt, PeriodicThread


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
            usage: List[float] = ...

            class Config:
                orm_mode = True

        content_format: WriteFormats = WriteFormats.text
        cpu_cores: List[CpuCoreModel] = []
        total_usage: List[str] = []
        period: float = ...

        class Config:
            orm_mode = True
            arbitrary_types_allowed = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.CPUModel

    def __init__(self, *args, tracked_by: LoggerCall, **kwargs):
        super().__init__(*args, tracked_by=tracked_by, **kwargs)

    def add_cpu_usage(self):
        cores = _get_cpu_usage()
        for idx, usage in enumerate(cores[:-1]):
            if idx >= len(self.cpu_cores):
                self.cpu_cores.append(self.CPUModel.CpuCoreModel(name='Core:' + str(idx), usage=[usage]))
            else:
                core = self.cpu_cores[idx]
                core.append(usage)
        self.total_usage.append(cores[-1])

    def _get_artifact_path(self, name):
        return os.path.join(str(id(self)), "cpu_usage", name)


class CpuILF(InjectionLogger):
    """This logger extracts the cpu information of your machine."""
    name = "CPULogger"
    uri = "https://www.padre-lab.eu/onto/cpu-logger"

    class CpuILFOutput(OutputModel):
        is_a: HttpUrl = "https://www.padre-lab.eu/onto/CpuILF-Output"

        cpu_usage: CpuTO.get_model_cls() = ...

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.CpuILFOutput

    _dependencies = {"psutil"}

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.text, _logger_call: LoggerCall, _logger_output,
                _pypads_period=1.0, _args, _kwargs,
                **kwargs):
        cpu_usage = CpuTO(tracked_by=_logger_call, content_format=_pypads_write_format)
        cpu_usage.period = _pypads_period

        def track_cpu_usage(to: CpuTO):
            to.add_cpu_usage()

        thread = PeriodicThread(target=track_cpu_usage, sleep=_pypads_period, args=(cpu_usage,))
        thread.start()

        # stop thread store disk_usage object
        def cleanup_thread(logger, _logger_call):
            thread.join()
            cpu_usage.store(_logger_output, key="cpu_usage")

        self.register_cleanup_fn(_logger_call, fn=cleanup_thread)


class RamTO(TrackedObject):
    """
    Function logging the memory information of the current pipeline object function call.
    """

    class RAMModel(TrackedObjectModel):
        uri: HttpUrl = "https://www.padre-lab.eu/onto/RamData"

        class MemoryModel(BaseModel):
            used: List[int] = ...
            free: List[int] = ...
            percentage: List[float] = ...
            type: str = ...

        content_format: WriteFormats = WriteFormats.json
        virtual_memory: MemoryModel = None
        swap_memory: MemoryModel = None
        period: float = ...

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

    def add_memory_usage(self):
        ram_info, swap_info = _get_memory_usage()

        used = ram_info.get('used')
        free = ram_info.get('free')
        percent = ram_info.get('percent')
        if self.virtual_memory is None:
            self.virtual_memory = self.RAMModel.MemoryModel(name='ram_usage', used=[used], free=[free],
                                                            percentage=[percent], type="RAM")
        else:
            self.virtual_memory.used.append(used)
            self.virtual_memory.free.append(free)
            self.virtual_memory.percentage.append(percent)

        used = swap_info.get('used')
        free = swap_info.get('free')
        percent = swap_info.get('percent')
        if self.swap_memory is None:
            self.swap_memory = self.RAMModel.MemoryModel(name='swap_usage', used=[used], free=[free],
                                                         percentage=[percent], type="Swap")
        else:
            self.swap_memory.used.append(used)
            self.swap_memory.free.append(free)
            self.swap_memory.percentage.append(percent)

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

        memory_usage: RamTO.RAMModel = ...

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.RamILFOutput

    _dependencies = {"psutil"}

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.json, _logger_call: LoggerCall, _logger_output,
                _pypads_period=1.0, _args, _kwargs, **kwargs):
        memory_usage = RamTO(tracked_by=_logger_call, content_format=_pypads_write_format)

        def track_mem_usage(to: RamTO):
            to.add_memory_usage()

        memory_usage.period = _pypads_period
        thread = PeriodicThread(target=track_mem_usage, args=(memory_usage,))
        thread.start()

        # stop thread store disk_usage object
        def cleanup_thread(logger, _logger_call):
            thread.join()
            memory_usage.store(_logger_output, key="memory_usage")

        self.register_cleanup_fn(_logger_call, fn=cleanup_thread)


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
            free: List[int] = ...
            used: List[int] = ...
            percentage: List[float] = ...

            class Config:
                orm_mode = True

        content_format: WriteFormats = WriteFormats.text
        partitions: List[PartitionModel] = []

        period: float = ...
        path: str = ...

        class Config:
            orm_mode = True
            arbitrary_types_allowed = True

    def __init__(self, *args, tracked_by: LoggerCall, path=None, **kwargs):
        self.path = path
        super().__init__(*args, tracked_by=tracked_by, **kwargs)

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.DiskModel

    def init_disk_usage(self):
        value = _get_disk_usage(self.path)
        for partition, info in value.get('partitions', dict()).items():
            _name = partition
            file_system = info.get('FileSystem')
            device = info.get('device')
            mount_point = info.get('MountPoint')
            free = [info.get('free')]
            used = [info.get('used')]
            percent = [info.get('percentage')]
            self.partitions.append(self.DiskModel.PartitionModel(name=_name, file_system=file_system,
                                                                 device=device, mount_point=mount_point, free=free,
                                                                 used=used,
                                                                 percentage=percent))

    def add_disk_usage(self):
        value = _get_disk_usage(self.path)
        for partition, info in value.get('partitions', dict()).items():
            for pm in self.partitions:
                if pm.name == partition:
                    pm.free.append(info.get('free'))
                    pm.used.append(info.get('used'))
                    pm.percentage.append(info.get('percentage'))

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
        disk_usage: List[DiskTO.DiskModel] = []

        class Config:
            orm_mode = True

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.DiskILFOutput

    @classmethod
    def _needed_packages(cls):
        return ["psutil"]

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.text, _logger_call: LoggerCall, _logger_output,
                _pypads_disk_usage=None, _pypads_period=1.0, _args, _kwargs,
                **kwargs):
        from pypads.app.base import PyPads
        from pypads.app.pypads import get_current_pads
        pads: PyPads = get_current_pads()
        if _pypads_disk_usage is None:
            _pypads_disk_usage = [local_uri_to_path(pads.uri)]

        def track_disk_usage(to: DiskTO):
            to.add_disk_usage()

        for p in _pypads_disk_usage:
            disk_usage_to = DiskTO(tracked_by=_logger_call, content_format=_pypads_write_format, path=p)
            disk_usage_to.init_disk_usage()
            disk_usage_to.period = _pypads_period
            thread = PeriodicThread(target=track_disk_usage, sleep=_pypads_period, args=(disk_usage_to,))
            thread.start()

            # stop thread store disk_usage object
            def cleanup_thread(logger, _logger_call):
                thread.join()
                disk_usage_to.store(_logger_output, key="disk_usage")

            self.register_cleanup_fn(_logger_call, fn=cleanup_thread)


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
