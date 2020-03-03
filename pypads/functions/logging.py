import datetime
import os
from logging import info, warning

import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads.logging_util import WriteFormats, to_folder_name, try_write_artifact
from pypads.mlflow.mlflow_autolog import _is_package_available
from pypads.util import sizeof_fmt


def _get_now():
    """
    Function for providing a current human readable timestamp.
    :return: timestamp
    """
    return datetime.datetime.now().strftime("%d_%b_%Y_%H-%M-%S.%f")


def log_init(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
             **kwargs):
    info("Pypads tracked class " + str(self.__class__) + " initialized.")
    _pypads_callback(*args, **kwargs)


def output(self, *args, write_format=WriteFormats.pickle, _pypads_wrappe, _pypads_context, _pypads_mapped_by,
           _pypads_callback,
           **kwargs):
    """
    Function logging the output of the current pipeline object function call.
    :param write_format: Format the artifact should write to
    :param self: Wrapper library object
    :param args: Input args to the real library call
    :param _pypads_wrappe: _pypads provided - wrapped library object
    :param _pypads_mapped_by: _pypads provided - wrapped library package
    :param _pypads_item: _pypads provided - wrapped function name
    :param _pypads_fn_stack: _pypads provided - stack of all the next functions to execute
    :param kwargs: Input kwargs to the real library call
    :return:
    """
    result = _pypads_callback(*args, **kwargs)
    name = os.path.join(to_folder_name(self, _pypads_context, _pypads_wrappe), "returns", str(id(_pypads_callback)))
    try_write_artifact(name, result, write_format)
    return result


def input(self, *args, write_format=WriteFormats.pickle, _pypads_wrappe, _pypads_context, _pypads_mapped_by,
          _pypads_callback,
          **kwargs):
    """
    Function logging the input parameters of the current pipeline object function call.
    :param write_format: Format the artifact should write to
    :param self: Wrapper library object
    :param args: Input args to the real library call
    :param _pypads_wrappe: _pypads provided - wrapped library object
    :param _pypads_mapped_by: _pypads provided - wrapped library package
    :param _pypads_item: _pypads provided - wrapped function name
    :param _pypads_fn_stack: _pypads provided - stack of all the next functions to execute
    :param kwargs: Input kwargs to the real library call
    :return:
    """
    for i in range(len(args)):
        arg = args[i]
        name = os.path.join(to_folder_name(self, _pypads_context, _pypads_wrappe), "args",
                            str(i) + "_" + str(id(_pypads_callback)))
        try_write_artifact(name, arg, write_format)

    for (k, v) in kwargs.items():
        name = os.path.join(to_folder_name(self, _pypads_context, _pypads_wrappe), "kwargs",
                            str(k) + "_" + str(id(_pypads_callback)))
        try_write_artifact(name, v, write_format)

    result = _pypads_callback(*args, **kwargs)
    return result


def cpu(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
    if _is_package_available("psutil"):
        import psutil
        cpu_usage = "CPU usage for cores:"
        for i, percentage in enumerate(psutil.cpu_percent(percpu=True)):
            cpu_usage += f"\nCore {i}: {percentage}%"
        cpu_usage += f"\nTotal CPU usage: {psutil.cpu_percent()}%"

        name = os.path.join(to_folder_name(self, _pypads_context, _pypads_wrappe), "cpu_usage")
        try_write_artifact(name, cpu_usage, WriteFormats.text)
    else:
        warning("To track cpu usage you need to install psutil.")
    result = _pypads_callback(*args, **kwargs)
    return result


def ram(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
    if _is_package_available("psutil"):
        import psutil
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        memory_usage = "Memory usage:"
        memory_usage += f"\n\tAvailable:{sizeof_fmt(memory.available)}"
        memory_usage += f"\n\tUsed:{sizeof_fmt(memory.used)}"
        memory_usage += f"\n\tPercentage:{sizeof_fmt(memory.percent)}"
        memory_usage += f"\nSwap usage::"
        memory_usage += f"\n\tFree:{sizeof_fmt(swap.free)}"
        memory_usage += f"\n\tUsed:{sizeof_fmt(memory.used)}"
        memory_usage += f"\n\tPercentage:{sizeof_fmt(memory.percent)}"

        name = os.path.join(to_folder_name(self, _pypads_context, _pypads_wrappe), "memory_usage")
        try_write_artifact(name, memory_usage, WriteFormats.text)
    else:
        warning("To track ram usage you need to install psutil.")
    result = _pypads_callback(*args, **kwargs)
    return result


def disk(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
    if _is_package_available("psutil"):
        import psutil
        # TODO https://www.thepythoncode.com/article/get-hardware-system-information-python
    else:
        warning("To track disk usage you need to install psutil.")
    result = _pypads_callback(*args, **kwargs)
    return result


def metric(self, *args, _pypads_wrappe, artifact_fallback=False, _pypads_context, _pypads_mapped_by, _pypads_callback,
           **kwargs):
    """
    Function logging the wrapped metric function
    :param self: Wrapper library object
    :param args: Input args to the real library call
    :param pypads_wrappe: pypads provided - wrapped library object
    :param pypads_package: pypads provided - wrapped library package
    :param pypads_item: pypads provided - wrapped function name
    :param pypads_fn_stack: pypads provided - stack of all the next functions to execute
    :param kwargs: Input kwargs to the real library call
    :return:
    """
    result = _pypads_callback(*args, **kwargs)

    if result is not None:
        if isinstance(result, float):
            try_mlflow_log(mlflow.log_metric, _pypads_wrappe.__name__ + ".txt", result)
        else:
            warning("Mlflow metrics have to be doubles. Could log the return value of type '" + str(
                type(result)) + "' of '" + _pypads_wrappe.__name__ + "' as artifact instead.")

            # TODO search callstack for already logged functions and ignore?
            if artifact_fallback:
                info("Logging result if '" + _pypads_wrappe.__name__ + "' as artifact.")
                try_write_artifact(_pypads_wrappe.__name__, str(result), WriteFormats.text)

    if self is not None:
        if result is self._pypads_wrapped:
            return self
    return result


def log(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
    print("Called following function: " + str(_pypads_wrappe) + " on " + str(
        _pypads_context) + " defined by mapping: " + str(_pypads_callback) + ". Next call is " + str(
        _pypads_callback))
