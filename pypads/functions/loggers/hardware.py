import os

from pypads.functions.analysis.call_tracker import LoggingEnv
from pypads.functions.loggers.base_logger import LoggingFunction
from pypads.logging_util import try_write_artifact, WriteFormats
from pypads.util import local_uri_to_path, sizeof_fmt


class Cpu(LoggingFunction):
    """
    This function only writes an information of a constructor execution to the stdout.
    """

    def _needed_packages(self):
        return ["psutil"]

    def __pre__(self, ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        name = os.path.join(_pypads_env.call.to_folder(), "pre_cpu_usage")
        try_write_artifact(name, _get_cpu_usage(), WriteFormats.text)

    def call_wrapped(self, ctx, *args, _pypads_env, _kwargs, **_pypads_hook_params):
        # TODO track while executing
        return super().call_wrapped(ctx, *args, _pypads_env=_pypads_env, _kwargs=_kwargs, **_pypads_hook_params)

    def __post__(self, ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        name = os.path.join(_pypads_env.call.to_folder(), "post_cpu_usage")
        try_write_artifact(name, _get_cpu_usage(), WriteFormats.text)


def _get_cpu_usage():
    import psutil
    cpu_usage = "CPU usage for cores:"
    for i, percentage in enumerate(psutil.cpu_percent(percpu=True)):
        cpu_usage += f"\nCore {i}: {percentage}%"
    cpu_usage += f"\nTotal CPU usage: {psutil.cpu_percent()}%"

    return cpu_usage


class Ram(LoggingFunction):
    """
    This function only writes an information of a constructor execution to the stdout.
    """

    def _needed_packages(self):
        return ["psutil"]

    def __pre__(self, ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        name = os.path.join(_pypads_env.call.to_folder(), "pre_memory_usage")
        try_write_artifact(name, _get_memory_usage(), WriteFormats.text)

    def call_wrapped(self, ctx, *args, _pypads_env, _kwargs, **_pypads_hook_params):
        # TODO track while executing
        return super().call_wrapped(ctx, *args, _pypads_env=_pypads_env, _kwargs=_kwargs, **_pypads_hook_params)

    def __post__(self, ctx, *args, _pypads_env: LoggingEnv, **kwargs):
        name = os.path.join(_pypads_env.call.to_folder(), "post_memory_usage")
        try_write_artifact(name, _get_memory_usage(), WriteFormats.text)


def _get_memory_usage():
    import psutil
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    memory_usage = "Memory usage:"
    memory_usage += f"\n\tAvailable:{sizeof_fmt(memory.available)}"
    memory_usage += f"\n\tUsed:{sizeof_fmt(memory.used)}"
    memory_usage += f"\n\tPercentage:{memory.percent}%"
    memory_usage += f"\nSwap usage::"
    memory_usage += f"\n\tFree:{sizeof_fmt(swap.free)}"
    memory_usage += f"\n\tUsed:{sizeof_fmt(memory.used)}"
    memory_usage += f"\n\tPercentage:{memory.percent}%"

    return memory_usage


class Disk(LoggingFunction):
    """
    This function only writes an information of a constructor execution to the stdout.
    """

    def _needed_packages(self):
        return ["psutil"]

    def __pre__(self, ctx, *args, _pypads_env, **kwargs):
        from pypads.base import PyPads, get_current_pads
        pads: PyPads = get_current_pads()
        path = local_uri_to_path(pads._uri)
        name = os.path.join(_pypads_env.call.to_folder(), "pre_disk_usage")
        try_write_artifact(name, _get_disk_usage(path), WriteFormats.text)

    def call_wrapped(self, ctx, *args, _pypads_env, _kwargs, **_pypads_hook_params):
        # TODO track while executing
        return super().call_wrapped(ctx, *args, _pypads_env=_pypads_env, _kwargs=_kwargs, **_pypads_hook_params)

    def __post__(self, ctx, *args, _pypads_env, **kwargs):
        from pypads.base import PyPads, get_current_pads
        pads: PyPads = get_current_pads()
        path = local_uri_to_path(pads._uri)
        name = os.path.join(_pypads_env.call.to_folder(), "post_disk_usage")
        try_write_artifact(name, _get_disk_usage(path), WriteFormats.text)


def _get_disk_usage(path):
    import psutil
    # TODO https://www.thepythoncode.com/article/get-hardware-system-information-python
    disk_usage = psutil.disk_usage(path)
    output_ = "Disk usage:"
    output_ += f"\n\tFree:{sizeof_fmt(disk_usage.free)}"
    output_ += f"\n\tUsed:{sizeof_fmt(disk_usage.used)}"
    output_ += f"\n\tPercentage:{disk_usage.percent}%"
    output_ += f"\nPartitions:"
    partitions = psutil.disk_partitions()
    for partition in partitions:
        output_ += f"\n+Partition1:"
        output_ += f"\n\tDevice:{partition.device}"
        output_ += f"\n\tMountpoint:{partition.mountpoint}"
        output_ += f"\n\tFile system:{partition.fstype}"
        output_ += f"\n\tStats:"
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            output_ += f"\n\t\t Busy!"
            continue
        output_ += f"\n\t\tFree:{partition_usage.free}"
        output_ += f"\n\t\tUsed:{partition_usage.used}"
        output_ += f"\n\t\tPercentage:{partition_usage.percent}%"
    return output_
