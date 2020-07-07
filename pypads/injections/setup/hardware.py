from pypads.app.injections.run_loggers import RunSetupFunction
from pypads.utils.util import sizeof_fmt, local_uri_to_path


class ISystem(RunSetupFunction):
    _dependencies = {"psutil"}

    def _call(self, pads, *args, **kwargs):
        import platform
        uname = platform.uname()
        pads.api.set_tag("pypads.system", uname.system)
        pads.api.set_tag("pypads.system.node", uname.node)
        pads.api.set_tag("pypads.system.release", uname.release)
        pads.api.set_tag("pypads.system.version", uname.version)
        pads.api.set_tag("pypads.system.machine", uname.machine)
        pads.api.set_tag("pypads.system.processor", uname.processor)


class ICpu(RunSetupFunction):
    _dependencies = {"psutil"}

    def _call(self, pads, *args, **kwargs):
        import psutil
        pads.api.set_tag("pypads.system.cpu.physical_cores", psutil.cpu_count(logical=False))
        pads.api.set_tag("pypads.system.cpu.total_cores", psutil.cpu_count(logical=True))
        freq = psutil.cpu_freq()
        pads.api.set_tag("pypads.system.cpu.max_freq", f"{freq.max:2f}Mhz")
        pads.api.set_tag("pypads.system.cpu.min_freq", f"{freq.min:2f}Mhz")


class IRam(RunSetupFunction):
    _dependencies = {"psutil"}

    def _call(self, pads, *args, **kwargs):
        import psutil
        memory = psutil.virtual_memory()
        pads.api.set_tag("pypads.system.memory.total", sizeof_fmt(memory.total))
        swap = psutil.swap_memory()
        pads.api.set_tag("pypads.system.swap.total", sizeof_fmt(swap.total))


class IDisk(RunSetupFunction):
    _dependencies = {"psutil"}

    def _call(self, pads, *args, **kwargs):
        import psutil
        # see https://www.thepythoncode.com/article/get-hardware-system-information-python
        path = local_uri_to_path(pads.backend.uri)
        disk_usage = psutil.disk_usage(path)
        pads.api.set_tag("pypads.system.disk.total", sizeof_fmt(disk_usage.total))


class IPid(RunSetupFunction):
    _dependencies = {"psutil"}

    def _call(self, pads, *args, **kwargs):
        import psutil
        import os
        pid = os.getpid()
        process = psutil.Process(pid=pid)
        pads.api.set_tag("pypads.system.process.id", pid)
        pads.api.set_tag("pypads.system.process.cwd", process.cwd())
        pads.api.set_tag("pypads.system.process.cpu_usage", str(process.cpu_percent()) + "%")
        pads.api.set_tag("pypads.system.process.memory_usage", str(process.memory_percent()) + "%")


class ISocketInfo(RunSetupFunction):

    def _call(self, pads, *args, **kwargs):
        import socket
        pads.api.set_tag("pypads.system.hostname", socket.gethostname())
        pads.api.set_tag("pypads.system.ip-address", socket.gethostbyname(socket.gethostname()))


class IMacAddress(RunSetupFunction):

    def _call(self, pads, *args, **kwargs):
        import re, uuid
        pads.api.set_tag("pypads.system.macaddress", ':'.join(re.findall('..', '%012x' % uuid.getnode())))

# def inetw(pads):
#     if is_package_available("psutil"):
#         import psutil
#         # get net stats
#
#     else:
#         logger.warning("To track network usage you need to install psutil.")
