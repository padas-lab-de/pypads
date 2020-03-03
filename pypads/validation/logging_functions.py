from logging import warning

import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log

from pypads.functions.logging import _get_now
from pypads.validation.generic_visitor import default_visitor


def parameters(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
               **kwargs):
    """
    Function logging the parameters of the current pipeline object function call.
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

    try:
        # prevent wrapped_class from becoming unwrapped
        visitor = default_visitor(self)

        for k, v in visitor[0]["steps"][0]["hyper_parameters"]["model_parameters"].items():
            try_mlflow_log(mlflow.log_param,
                           _pypads_mapped_by.reference + "." + str(id(self)) + "." + _get_now() + "." + k + ".txt", v)
    except Exception as e:
        warning("Couldn't use visitor for parameter extraction. " + str(e) + " Omit logging for now.")
        # for i in range(len(args)):
        #    arg = args[i]
        #    try_mlflow_log(mlflow.log_param, _pypads_mapped_by + "." + str(id(self)) + "." + get_now() + ".args." + str(i), str(arg))
        #
        # for (k, v) in kwargs.items():
        #    try_mlflow_log(mlflow.log_param, _pypads_mapped_by + "." + str(id(self)) + "." + get_now() + ".kwargs." + str(k), str(v))

    return result
