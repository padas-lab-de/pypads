import uuid
from typing import Type, Union, Optional, List

from pydantic import BaseModel

from pypads.app.env import LoggerEnv
from pypads.app.injections.run_loggers import RunSetup
from pypads.app.injections.tracked_object import TrackedObject
from pypads.app.misc.mixins import DEFAULT_ORDER
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.util import sizeof_fmt, uri_to_path, PeriodicThread


class ComputerTO(TrackedObject):
    """
    Tracked object to represent a single computing node.
    """

    class ComputerTOModel(TrackedObjectModel):
        """
        Model class containing references to the real hardware information and a mac address
        """
        category: str = "Computer"
        description: str = "Information about the in the experiment used computer."
        mac_address: str = ...
        cpu: Optional[str] = ...  # CPU TrackedObject
        memory: Optional[str] = ...  # Memory TrackedObject
        disk: Optional[str] = ...  # Disk TrackedObject
        system: Optional[str] = ...  # System TrackedObject
        process: Optional[str] = ...  # Process TrackedObject
        network: Optional[str] = ...  # Network TrackedObject

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.ComputerTOModel


class IMacAddressRSF(RunSetup):
    """
    Run setup function to create the ComputerTO and store it for further additions into the cache.
    """
    name = "Generic MacAddress Run Setup Logger"
    category: str = "MacAddressRunLogger"

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, order=order if order is not None else DEFAULT_ORDER, **kwargs)

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        import re, uuid
        cto = ComputerTO(mac_address=':'.join(re.findall('..', '%012x' % uuid.getnode())),
                         parent=_logger_output)
        _pypads_env.pypads.cache.run_add(ComputerTO.__name__, cto)
        cto.store()


class SystemTO(TrackedObject):
    class SystemTOModel(TrackedObjectModel):
        category: str = "SystemInformation"
        description: str = "Information about the in the experiment used system."
        system: str = ...
        node: str = ...
        release: str = ...
        version: str = ...
        machine: str = ...
        processor: str = ...

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.SystemTOModel


class ISystemRSF(RunSetup):
    """
    System run setup function running after IMacAddressRSF (see order) and updating the ComputerTO (see _needed_cached)
    """
    _dependencies = {"psutil"}
    _needed_cached = ComputerTO.__name__
    name = "Generic System Run Setup Logger"
    category: str = "SystemRumLogger"

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, order=order if order is not None else DEFAULT_ORDER + 1, **kwargs)

    def _call(self, *args, _pypads_env: LoggerEnv, _pypads_cached_results=None, _logger_call, _logger_output, **kwargs):
        import platform
        system = platform.uname()
        computer_to: ComputerTO = _pypads_cached_results[0]
        system_info = SystemTO(system=system.system, node=system.node, release=system.release, version=system.version,
                               machine=system.machine, processor=system.processor, parent=_logger_output)

        # Update computer to
        computer_to.system = system_info.store()
        computer_to.store()


class CpuTO(TrackedObject):
    class CpuTOModel(TrackedObjectModel):
        category: str = "CpuInformation"
        description: str = "Information about the in the experiment used cpu."
        physical_cores: int = ...
        total_cores: int = ...
        max_freq: str = ...
        min_freq: str = ...

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.CpuTOModel


class CpuUsageTO(TrackedObject):
    """
    Tracked object to be updated live on the cpu usage.
    """

    class CpuUsageTOModel(TrackedObjectModel):
        category: str = "CpuUsage"
        description: str = "Timeline about the usage of the in the experiment used cpu."

        class CpuCoreModel(BaseModel):
            index: int = ...
            usage: List[float] = ...

            class Config:
                orm_mode = True

        cpu_cores: List[CpuCoreModel] = []
        total_usage: List[str] = []
        period: float = ...

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.CpuUsageTOModel

    def add_cpu_usage(self: Union['CpuUsageTO', CpuUsageTOModel]):
        cores = _get_cpu_usage()
        for idx, usage in enumerate(cores[:-1]):
            if idx >= len(self.cpu_cores):
                self.cpu_cores.append(self.__class__.CpuUsageTOModel.CpuCoreModel(index=idx, usage=[usage]))
            else:
                core = self.cpu_cores[idx]
                core.usage.append(usage)
        self.total_usage.append(cores[-1])


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


class ICpuRSF(RunSetup):
    _dependencies = {"psutil"}
    _needed_cached = ComputerTO.__name__
    name = "Generic CPU Run Setup Logger"
    category: str = "CPURunLogger"

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, order=order if order is not None else DEFAULT_ORDER + 1, **kwargs)

    class ICpuRSFOutput(OutputModel):
        category: str = "ISystemRSF-Output"
        cpu: Union[uuid.UUID, str] = ...  # CpuTO
        cpu_usage: Optional[Union[uuid.UUID, str]] = ...  # CpuUsageTO

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.ICpuRSFOutput

    def _call(self, *args, _pypads_period=1.0, _pypads_env: LoggerEnv, _logger_call, _logger_output,
              _pypads_cached_results=None, **kwargs):
        import psutil
        freq = psutil.cpu_freq()
        computer_to: ComputerTO = _pypads_cached_results[0]
        cpu_info = CpuTO(physical_cores=psutil.cpu_count(logical=False), total_cores=psutil.cpu_count(logical=True),
                         max_freq=f"{freq.max:2f}Mhz", min_freq=f"{freq.min:2f}Mhz", parent=_logger_output)

        # Update computer to
        cpu_ref = cpu_info.store()
        _logger_output.cpu = cpu_ref
        computer_to.cpu = cpu_ref
        computer_to.store()

        if _pypads_period > 0:
            cpu_usage_info = CpuUsageTO(parent=_logger_output)
            cpu_usage_info.period = _pypads_period

            def track_cpu_usage(to: CpuUsageTO):
                to.add_cpu_usage()
                to.store()

            _logger_output.cpu_usage = cpu_usage_info.store()
            thread = PeriodicThread(target=track_cpu_usage, sleep=_pypads_period, args=(cpu_usage_info,))
            thread.start()

            # stop thread store disk_usage object
            def cleanup_thread(*args, **kwargs):
                thread.join()

            _pypads_env.pypads.api.register_teardown_utility(_logger_call, fn=cleanup_thread)


class RamTO(TrackedObject):
    class RamTOModel(TrackedObjectModel):
        category: str = "RamInformation"
        description: str = "Information about the in the experiment used ram."
        total_memory: str = ...
        total_swap: str = ...

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.RamTOModel


class IRamRSF(RunSetup):
    _dependencies = {"psutil"}
    _needed_cached = ComputerTO.__name__
    name = "Generic Ram Run Setup Logger"
    category: str = "RamRunLogger"

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, order=order if order is not None else DEFAULT_ORDER + 1, **kwargs)

    def _call(self, *args, _pypads_period=1.0, _pypads_env: LoggerEnv, _logger_call, _logger_output,
              _pypads_cached_results=None, **kwargs):
        import psutil
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        computer_to: ComputerTO = _pypads_cached_results[0]
        memory_info = RamTO(total_memory=sizeof_fmt(memory.total), total_swap=sizeof_fmt(swap.total),
                            parent=_logger_output)

        computer_to.memory = memory_info.store()
        computer_to.store()


class DiskTO(TrackedObject):
    class DiskTOModel(TrackedObjectModel):
        category: str = "DiskInformation"
        description: str = "Information about the in the experiment used disk."
        total_size: str = ...
        free: str = ...

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.DiskTOModel


class IDiskRSF(RunSetup):
    _dependencies = {"psutil"}
    _needed_cached = ComputerTO.__name__
    name = "Disk Run Setup Logger"
    category: str = "DiskRunLogger"

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, order=order if order is not None else DEFAULT_ORDER + 1, **kwargs)

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, _pypads_cached_results=None, **kwargs):
        import psutil
        pads = _logger_call._logging_env.pypads
        path = uri_to_path(pads.backend.uri)
        disk_usage = psutil.disk_usage(path)
        computer_to: ComputerTO = _pypads_cached_results[0]
        disk_info = DiskTO(total_size=disk_usage.total, free=disk_usage.free, parent=_logger_output)

        computer_to.disk = disk_info.store()
        computer_to.store()


class ProcessTO(TrackedObject):
    class ProcessTOModel(TrackedObjectModel):
        category: str = "ProcessInformation"
        description: str = "Information about the in the experiment used main process."
        id: str = ...
        cwd: str = ...

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.ProcessTOModel


class IPidRSF(RunSetup):
    _dependencies = {"psutil"}
    _needed_cached = ComputerTO.__name__
    name = "Process Run Setup Logger"
    category: str = "ProcessRunLogger"

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, order=order if order is not None else DEFAULT_ORDER + 1, **kwargs)

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, _pypads_cached_results=None, **kwargs):
        import psutil
        import os
        pid = os.getpid()
        process = psutil.Process(pid=pid)
        computer_to: ComputerTO = _pypads_cached_results[0]
        process_info = ProcessTO(id=pid, cwd=process.cwd(), parent=_logger_output)

        computer_to.process = process_info.store()
        computer_to.store()


class SocketTO(TrackedObject):
    class SocketTOModel(TrackedObjectModel):
        category: str = "ProcessInformation"
        description: str = "Information about the in the experiment used main process."
        hostname: str = ...
        ip: str = ...

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.SocketTOModel


class ISocketInfoRSF(RunSetup):
    name = "Socket Run Setup Logger"
    category: str = "SockerRunLogger"
    _needed_cached = ComputerTO.__name__

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, order=order if order is not None else DEFAULT_ORDER + 1, **kwargs)

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, _pypads_cached_results=None, **kwargs):
        computer_to: ComputerTO = _pypads_cached_results[0]
        import socket
        socket_info = SocketTO(hostname=socket.gethostname(), ip=socket.gethostbyname(socket.gethostname()),
                               parent=_logger_output)

        computer_to.network = socket_info.store()
        computer_to.store()
