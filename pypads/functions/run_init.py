from logging import warning

from pypads.mlflow.mlflow_autolog import _is_package_available
from pypads.util import sizeof_fmt, local_uri_to_path


def isystem(pads):
    import platform
    uname = platform.uname()
    pads.api.set_tag("pypads.system", uname.system)
    pads.api.set_tag("pypads.system.node", uname.node)
    pads.api.set_tag("pypads.system.release", uname.release)
    pads.api.set_tag("pypads.system.version", uname.version)
    pads.api.set_tag("pypads.system.machine", uname.machine)
    pads.api.set_tag("pypads.system.processor", uname.processor)


def icpu(pads):
    if _is_package_available("psutil"):
        import psutil
        pads.api.set_tag("pypads.system.cpu.physical_cores", psutil.cpu_count(logical=False))
        pads.api.set_tag("pypads.system.cpu.total_cores", psutil.cpu_count(logical=True))
        freq = psutil.cpu_freq()
        pads.api.set_tag("pypads.system.cpu.max_freq", f"{freq.max:2f}Mhz")
        pads.api.set_tag("pypads.system.cpu.min_freq", f"{freq.min:2f}Mhz")
    else:
        warning("To track cpu usage you need to install psutil.")


def iram(pads):
    if _is_package_available("psutil"):
        import psutil
        memory = psutil.virtual_memory()
        pads.api.set_tag("pypads.system.memory.total", sizeof_fmt(memory.total))
        swap = psutil.swap_memory()
        pads.api.set_tag("pypads.system.swap.total", sizeof_fmt(swap.total))
    else:
        warning("To track ram usage you need to install psutil.")


def idisk(pads):
    if _is_package_available("psutil"):
        import psutil
        # TODO https://www.thepythoncode.com/article/get-hardware-system-information-python
        path = local_uri_to_path(pads._uri)
        disk_usage = psutil.disk_usage(path)
        pads.api.set_tag("pypads.system.disk.total", sizeof_fmt(disk_usage.total))
        # partitions = psutil.disk_partitions()
        # for partition in partitions:
        #     try:
        #         pads.api.set_tag("pypads.system.partition-{}.total".format(partition.device.replace("/", "-")),
        #                          sizeof_fmt(psutil.disk_usage(partition.mountpoint).total))
        #     except PermissionError:
        #         continue

    else:
        warning("To track disk usage you need to install psutil.")

def ipid(pads):
    if _is_package_available("psutil"):
        import psutil
        import os
        pid = os.getpid()
        process = psutil.Process(pid=pid)
        pads.api.set_tag("pypads.system.process.cwd", process.cwd())
        pads.api.set_tag("pypads.system.process.cpu_usage", str(process.cpu_percent())+"%")
        pads.api.set_tag("pypads.system.process.memory_usage", str(process.memory_percent())+"%")
    else:
        warning("To track current running process you need to install psutil")

def inetw(pads):
    if _is_package_available("psutil"):
        import psutil
        # TODO

    else:
        warning("To track network usage you need to install psutil.")
