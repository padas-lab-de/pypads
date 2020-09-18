from typing import Type, List

from pydantic.main import BaseModel
from pydantic.networks import HttpUrl

from pypads.app.env import LoggerEnv
from pypads.app.injections.base_logger import TrackedObject, LoggerCall
from pypads.app.injections.run_loggers import RunSetup
from pypads.arguments import ontology_uri
from pypads.model.logger_output import OutputModel, TrackedObjectModel
from pypads.utils.util import sizeof_fmt, local_uri_to_path


class HardwareTO(TrackedObject):
    """
    Tracking object class for System info, i.e: cpu, os, memory, disk
    """

    class HardwareModel(TrackedObjectModel):
        uri: HttpUrl = f"{ontology_uri}env/hardware-information"
        name: str = "Hardware Info"
        tags: List[str] = []

        class Config:
            orm_mode = True

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.HardwareModel

    def __init__(self, *args, tracked_by: LoggerCall, name: str, uri: str, **kwargs):
        super().__init__(*args, tracked_by=tracked_by, name=name, uri=uri, **kwargs)

    def add_tag(self, key, value, description):
        self.tags.append(key)
        self.store_tag(key, value, description=description)


class ISystemRSF(RunSetup):
    _dependencies = {"psutil"}

    name = "System Run Setup Logger"
    uri = f"{ontology_uri}system-run-logger"

    class ISystemRSFOutput(OutputModel):
        is_a: HttpUrl = f"{ontology_uri}ISystemRSF-Output"
        system_info: str = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.ISystemRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        import platform
        uname = platform.uname()
        system_info = HardwareTO(name="System Info", tracked_by=_logger_call,
                                 uri=f"{ontology_uri}env/system-information")

        system_info.add_tag("pypads.system", uname.system, description="Operating system")
        system_info.add_tag("pypads.system.node", uname.node, description="Operating system node")
        system_info.add_tag("pypads.system.release", uname.release, description="Operating system release")
        system_info.add_tag("pypads.system.version", uname.version, description="Operating system version")
        system_info.add_tag("pypads.system.machine", uname.machine, description="Operating system machine")
        system_info.add_tag("pypads.system.processor", uname.processor, description="Processor technology")
        self.system_info = system_info.store(_logger_output, "system_info")


class ICpuRSF(RunSetup):
    _dependencies = {"psutil"}
    name = "CPU Run Setup Logger"
    uri = f"{ontology_uri}cpu-run-logger"

    class ICpuRSFOutput(OutputModel):
        is_a: HttpUrl = f"{ontology_uri}ICpuRSF-Output"
        cpu_info: HardwareTO.get_model_cls() = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.ICpuRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        import psutil
        cpu_info = HardwareTO(name="Cpu Info", tracked_by=_logger_call,
                              uri=f"{ontology_uri}env/cpu-information")
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
    name = "Ram Run Setup Logger"
    uri = f"{ontology_uri}ram-run-logger"

    class IRamRSFOutput(OutputModel):
        is_a: HttpUrl = f"{ontology_uri}IRamRSF-Output"
        memory_info: HardwareTO.get_model_cls() = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.IRamRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        memory_info = HardwareTO(name="Memory Info", tracked_by=_logger_call,
                                 uri=f"{ontology_uri}env/memory-information")
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
    uri = f"{ontology_uri}disk-run-logger"

    class IDiskRSFOutput(OutputModel):
        is_a: HttpUrl = f"{ontology_uri}IDiskRSF-Output"
        disk_info: HardwareTO.get_model_cls() = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.IDiskRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        disk_info = HardwareTO(name="Disk Info", tracked_by=_logger_call,
                               uri=f"{ontology_uri}env/disk-information")
        import psutil
        # see https://www.thepythoncode.com/article/get-hardware-system-information-python
        pads = _logger_call._logging_env.pypads
        path = local_uri_to_path(pads.backend.uri)
        disk_usage = psutil.disk_usage(path)
        disk_info.store_tag("pypads.system.disk.total", sizeof_fmt(disk_usage.total), description="Total disk usage")
        disk_info.store(_logger_output, "disk_info")


class IPidRSF(RunSetup):
    _dependencies = {"psutil"}
    name = "Process Run Setup Logger"
    uri = f"{ontology_uri}process-run-logger"

    class IPidRSFOutput(OutputModel):
        is_a: HttpUrl = f"{ontology_uri}IPidRSF-Output"
        process_info: HardwareTO.get_model_cls() = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.IPidRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        process_info = HardwareTO(name="Process Info", tracked_by=_logger_call,
                                  uri=f"{ontology_uri}env/process-information")
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
    uri = f"{ontology_uri}socket-run-logger"

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.ISocketInfoRSFOutput

    class ISocketInfoRSFOutput(OutputModel):
        is_a: HttpUrl = f"{ontology_uri}ISocketInfoRSF-Output"
        socket_info: HardwareTO.get_model_cls() = ...

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        socket_info = HardwareTO(name="Socket Info", tracked_by=_logger_call,
                                 uri=f"{ontology_uri}env/socker-information")
        import socket
        socket_info.add_tag("pypads.system.hostname", socket.gethostname(), description="Hostname of open socket")
        socket_info.add_tag("pypads.system.ip-address", socket.gethostbyname(socket.gethostname()),
                            description="Ip address of open socket")
        socket_info.store(_logger_output, "socket_info")


class IMacAddressRSF(RunSetup):
    name = "MacAddress Run Setup Logger"
    uri = f"{ontology_uri}macaddress-run-logger"

    class IMacAddressRSFOutput(OutputModel):
        is_a: HttpUrl = f"{ontology_uri}IMacAddressRSF-Output"
        mac_address: HardwareTO.get_model_cls() = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.IMacAddressRSFOutput

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        mac_address = HardwareTO(name="Mac Address", tracked_by=_logger_call,
                                 uri=f"{ontology_uri}env/mac-address-information")
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
