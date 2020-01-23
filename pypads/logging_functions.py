import datetime
from logging import warning

import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads.bindings.generic_visitor import default_visitor
from pypads.logging_util import try_write_artifact, WriteFormats


def get_now():
    """
    Function for providing a current human readable timestamp.
    :return: timestamp
    """
    return datetime.datetime.now().strftime("%d_%b_%Y_%H-%M-%S.%f")


def parameters(self, *args, pypads_wrappe, pypads_package, pypads_item, pypads_fn_stack, **kwargs):
    """
    Function logging the parameters of the current pipeline object function call.
    :param self: Wrapper library object
    :param args: Input args to the real library call
    :param pypads_wrappe: pypads provided - wrapped library object
    :param pypads_package: pypads provided - wrapped library package
    :param pypads_item: pypads provided - wrapped function name
    :param pypads_fn_stack: pypads provided - stack of all the next functions to execute
    :param kwargs: Input kwargs to the real library call
    :return:
    """
    result = pypads_fn_stack.pop()(*args, **kwargs)

    try:
        # prevent wrapped_class from becoming unwrapped
        visitor = default_visitor(self)

        for k, v in visitor[0]["steps"][0]["hyper_parameters"]["model_parameters"].items():
            try_mlflow_log(mlflow.log_param, pypads_package + "." + str(id(self)) + "." + get_now() + "." + k, v)
    except ValueError as e:
        warning("Couldn't use visitor for parameter extraction. " + str(e) + " Omit logging for now.")
        # for i in range(len(args)):
        #    arg = args[i]
        #    try_mlflow_log(mlflow.log_param, pypads_package + "." + str(id(self)) + "." + get_now() + ".args." + str(i), str(arg))
        #
        # for (k, v) in kwargs.items():
        #    try_mlflow_log(mlflow.log_param, pypads_package + "." + str(id(self)) + "." + get_now() + ".kwargs." + str(k), str(v))

    if result is self._pads_wrapped_instance:
        return self
    return result


def output(self, *args, write_format=WriteFormats.pickle, pypads_wrappe, pypads_package, pypads_item, pypads_fn_stack,
           **kwargs):
    """
    Function logging the output of the current pipeline object function call.
    :param write_format: Format the artifact should write to
    :param self: Wrapper library object
    :param args: Input args to the real library call
    :param pypads_wrappe: pypads provided - wrapped library object
    :param pypads_package: pypads provided - wrapped library package
    :param pypads_item: pypads provided - wrapped function name
    :param pypads_fn_stack: pypads provided - stack of all the next functions to execute
    :param kwargs: Input kwargs to the real library call
    :return:
    """
    result = pypads_fn_stack.pop()(*args, **kwargs)
    name = pypads_wrappe.__name__ + "." + str(id(self)) + "." + get_now() + "." + pypads_item + ".return"
    try_write_artifact(name, result, write_format)
    if result is self._pads_wrapped_instance:
        return self
    return result


def input(self, *args, write_format=WriteFormats.pickle, pypads_wrappe, pypads_package, pypads_item, pypads_fn_stack,
          **kwargs):
    """
    Function logging the input parameters of the current pipeline object function call.
    :param write_format: Format the artifact should write to
    :param self: Wrapper library object
    :param args: Input args to the real library call
    :param pypads_wrappe: pypads provided - wrapped library object
    :param pypads_package: pypads provided - wrapped library package
    :param pypads_item: pypads provided - wrapped function name
    :param pypads_fn_stack: pypads provided - stack of all the next functions to execute
    :param kwargs: Input kwargs to the real library call
    :return:
    """
    for i in range(len(args)):
        arg = args[i]
        name = pypads_wrappe.__name__ + "." + str(id(self)) + "." + get_now() + "." + pypads_item + ".args." + str(
            i)
        try_write_artifact(name, arg, write_format)

    for (k, v) in kwargs.items():
        name = pypads_wrappe.__name__ + "." + str(
            id(self)) + "." + get_now() + "." + pypads_item + ".kwargs." + k
        try_write_artifact(name, v, write_format)

    result = pypads_fn_stack.pop()(*args, **kwargs)
    if result is self._pads_wrapped_instance:
        return self
    return result


def cpu(self, *args, pypads_wrappe, pypads_package, pypads_item, pypads_fn_stack, **kwargs):
    import platform
    mlflow.set_tag("pypads.processor", platform.processor())
