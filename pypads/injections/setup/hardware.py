from typing import Type, List

from pydantic.main import BaseModel

from pypads.app.env import LoggerEnv
from pypads.app.injections.base_logger import TrackedObject, LoggerOutput
from pypads.app.injections.run_loggers import RunSetup
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.util import sizeof_fmt, uri_to_path


class HardwareTO(TrackedObject):
    """
    Tracking object class for System info, i.e: cpu, os, memory, disk
    """

    class HardwareModel(TrackedObjectModel):
        category: str = "HardwareInformation"
        name: str = "Hardware Info"
        tags: List[str] = []

        class Config:
            orm_mode = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.HardwareModel

    def __init__(self, *args, part_of: LoggerOutput, name: str, **kwargs):
        super().__init__(*args, part_of=part_of, name=name, **kwargs)

    def add_tag(self, key, value, description):
        self.tags.append(key)
        self.store_tag(key, value, description=description)


class ISystemRSF(RunSetup):
    _dependencies = {"psutil"}

    name = "Generic System Run Setup Logger"
    category: str = "SystemRumLogger"

    class ISystemRSFOutput(OutputModel):
        category: str = "ISystemRSF-Output"
        system_info: str = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.ISystemRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        import platform
        uname = platform.uname()
        system_info = HardwareTO(name="System Info", part_of=_logger_output)

        system_info.add_tag("pypads.system", uname.system, description="Operating system")
        system_info.add_tag("pypads.system.node", uname.node, description="Operating system node")
        system_info.add_tag("pypads.system.release", uname.release, description="Operating system release")
        system_info.add_tag("pypads.system.version", uname.version, description="Operating system version")
        system_info.add_tag("pypads.system.machine", uname.machine, description="Operating system machine")
        system_info.add_tag("pypads.system.processor", uname.processor, description="Processor technology")
        self.system_info = system_info.store(_logger_output, "system_info")


class ICpuRSF(RunSetup):
    _dependencies = {"psutil"}
    name = "Generic CPU Run Setup Logger"
    category: str = "CPURunLogger"

    class ICpuRSFOutput(OutputModel):
        category: str = "ICpuRSF-Output"
        cpu_info: str = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.ICpuRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        import psutil
        cpu_info = HardwareTO(name="Cpu Info", part_of=_logger_output)
        cpu_info.store_tag("pypads.system.cpu.physical_cores", psutil.cpu_count(logical=False),
                           description="Number of physical cores")
        cpu_info.store_tag("pypads.system.cpu.total_cores", psutil.cpu_count(logical=True),
                           description="Number of total cores")
        freq = psutil.cpu_freq()
        cpu_info.store_tag("pypads.system.cpu.max_freq", f"{freq.max:2f}Mhz",
                           description="Maximum processor frequency in (Mhz)")
        cpu_info.store_tag("pypads.system.cpu.min_freq", f"{freq.min:2f}Mhz",
                           description="Minimum processor frequencyin (Mhz)")
        cpu_info.store(_logger_output, "cpu_info")


class IRamRSF(RunSetup):
    _dependencies = {"psutil"}
    name = "Generic Ram Run Setup Logger"
    category: str = "RamRunLogger"

    class IRamRSFOutput(OutputModel):
        category: str = "IRamRSF-Output"
        memory_info: str = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.IRamRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        memory_info = HardwareTO(name="Memory Info", part_of=_logger_output)
        import psutil
        memory = psutil.virtual_memory()
        memory_info.store_tag("pypads.system.memory.total", sizeof_fmt(memory.total),
                              description="Total virtual memory RAM")
        swap = psutil.swap_memory()
        memory_info.store_tag("pypads.system.swap.total", sizeof_fmt(swap.total), description="Total swap memory")
        memory_info.store(_logger_output, "memory_info")


class IDiskRSF(RunSetup):
    _dependencies = {"psutil"}
    name = "Disk Run Setup Logger"
    category: str = "DiskRunLogger"

    class IDiskRSFOutput(OutputModel):
        category: str = "IDiskRSF-Output"
        disk_info: str = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.IDiskRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        disk_info = HardwareTO(name="Disk Info", part_of=_logger_output)
        import psutil
        # see https://www.thepythoncode.com/article/get-hardware-system-information-python
        pads = _logger_call._logging_env.pypads
        path = uri_to_path(pads.backend.uri)
        disk_usage = psutil.disk_usage(path)
        disk_info.store_tag("pypads.system.disk.total", sizeof_fmt(disk_usage.total), description="Total disk usage")
        disk_info.store(_logger_output, "disk_info")


class IPidRSF(RunSetup):
    _dependencies = {"psutil"}
    name = "Process Run Setup Logger"
    category: str = "ProcessRunLogger"

    class IPidRSFOutput(OutputModel):
        category: str = "IPidRSF-Output"
        process_info: str = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.IPidRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        process_info = HardwareTO(name="Process Info", part_of=_logger_output)
        import psutil
        import os
        pid = os.getpid()
        process = psutil.Process(pid=pid)
        process_info.add_tag("pypads.system.process.id", pid, description="Process ID (PID)")
        process_info.add_tag("pypads.system.process.cwd", process.cwd(),
                             description="Process current working directory")
        process_info.add_tag("pypads.system.process.cpu_usage", str(process.cpu_percent()) + "%",
                             description="Process cpu usage")
        process_info.add_tag("pypads.system.process.memory_usage", str(process.memory_percent()) + "%",
                             description="Process memroy usage")
        process_info.store(_logger_output, "process_info")


class ISocketInfoRSF(RunSetup):
    name = "Socket Run Setup Logger"
    category: str = "SockerRunLogger"

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.ISocketInfoRSFOutput

    class ISocketInfoRSFOutput(OutputModel):
        category: str = "ISocketInfoRSF-Output"
        socket_info: str = ...

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        socket_info = HardwareTO(name="Socket Info", part_of=_logger_output)
        import socket
        socket_info.add_tag("pypads.system.hostname", socket.gethostname(), description="Hostname of open socket")
        socket_info.add_tag("pypads.system.ip-address", socket.gethostbyname(socket.gethostname()),
                            description="Ip address of open socket")
        socket_info.store(_logger_output, "socket_info")


class IMacAddressRSF(RunSetup):
    name = "Generic MacAddress Run Setup Logger"
    category: str = "MacAddressRunLogger"

    class IMacAddressRSFOutput(OutputModel):
        category: str = "IMacAddressRSF-Output"
        mac_address: str = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.IMacAddressRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        mac_address = HardwareTO(name="Mac Address", part_of=_logger_output)
        import re, uuid
        mac_address.add_tag("pypads.system.macaddress", ':'.join(re.findall('..', '%012x' % uuid.getnode())),
                            description="Mac Address")
        mac_address.store(_logger_output, "mac_address")

# def inetw(pads):
#     if is_package_available("psutil"):
#         import psutil
#         # get net stats
#
#     else:
#         logger.warning("To track network usage you need to install psutil.")
