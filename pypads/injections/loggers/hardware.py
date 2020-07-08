import os
from typing import List

from pydantic import BaseModel

from pypads.app.injections.base_logger import LoggingFunction, LoggerCall, LoggerTrackingObject
from pypads.injections.analysis.call_tracker import LoggingEnv
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


class CPUTO(LoggerTrackingObject):
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
                arbitrary_types_allowed = True

        input: List[ParamModel] = []
        call: LoggerCallModel = ...

        class Config:
            orm_mode = True

    def __init__(self, *args, call: LoggerCall, **kwargs):
        super().__init__(*args, model_cls=self.CPUModel, call=call, **kwargs)

    def add_arg(self, name, value, format):
        self._add_param(name, value, format, 0)

    def add_kwarg(self, name, value, format):
        self._add_param(name, value, format, "kwarg")

    def _add_param(self, name, value, format, type):
        # TODO try to extract parameter documentation?
        index = len(self.input)
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
        return [CPUTO.CPUModel.schema()]

    _dependencies = {"psutil"}

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.text, _logger_call: LoggerCall, _args, _kwargs, **kwargs):

        inputs = CPUTO(call=_logger_call)
        inputs.add_arg("pre_cpu_usage", _get_cpu_usage(), _pypads_write_format)

        """
        name = os.path.join(_logger_call.call.to_folder(), "pre_cpu_usage")
        try_write_artifact(name, _get_cpu_usage(), WriteFormats.text)
        """

    def __call_wrapped__(self, ctx, *args, _pypads_env, _args, _kwargs, **_pypads_hook_params):
        # TODO track while executing instead of before and after
        return super().__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=_args, _kwargs=_kwargs,
                                        **_pypads_hook_params)

    def __post__(self, ctx, *args, _pypads_write_format=WriteFormats.text, _logger_call, _pypads_result, **kwargs):
        output = CPUTO(call=_logger_call)
        output.add_arg("post_cpu_usage", _get_cpu_usage(), _pypads_write_format)


class Ram(LoggingFunction):
    """
    This function only writes an information of a constructor execution to the stdout.
    """

    _dependencies = {"psutil"}

    def __pre__(self, ctx, *args, _logger_call: LoggingEnv, **kwargs):
        name = os.path.join(_logger_call.call.to_folder(), "pre_memory_usage")
        try_write_artifact(name, _get_memory_usage(), WriteFormats.text)

    def __call_wrapped__(self, ctx, *args, _pypads_env, _args, _kwargs, **_pypads_hook_params):
        # TODO track while executing instead of before and after
        return super().__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=_args, _kwargs=_kwargs,
                                        **_pypads_hook_params)

    def __post__(self, ctx, *args, _logger_call: LoggingEnv, **kwargs):
        name = os.path.join(_logger_call.call.to_folder(), "post_memory_usage")
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

    @classmethod
    def _needed_packages(cls):
        return ["psutil"]

    def __pre__(self, ctx, *args, _logger_call, **kwargs):
        from pypads.app.base import PyPads
        from pypads.app.pypads import get_current_pads
        pads: PyPads = get_current_pads()
        path = local_uri_to_path(pads.uri)
        name = os.path.join(_logger_call.call.to_folder(), "pre_disk_usage")
        try_write_artifact(name, _get_disk_usage(path), WriteFormats.text)

    def __call_wrapped__(self, ctx, *args, _pypads_env, _args, _kwargs, **_pypads_hook_params):
        # TODO track while executing instead of before and after
        return super().__call_wrapped__(ctx, _pypads_env=_pypads_env, _args=_args, _kwargs=_kwargs,
                                        **_pypads_hook_params)

    def __post__(self, ctx, *args, _logger_call, **kwargs):
        from pypads.app.base import PyPads
        from pypads.app.pypads import get_current_pads
        pads: PyPads = get_current_pads()
        path = local_uri_to_path(pads.uri)
        name = os.path.join(_logger_call.call.to_folder(), "post_disk_usage")
        try_write_artifact(name, _get_disk_usage(path), WriteFormats.text)


def _get_disk_usage(path):
    import psutil
    # See https://www.thepythoncode.com/article/get-hardware-system-information-python
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
