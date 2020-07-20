import sys

import gorilla
from mlflow.utils import experimental

from pypads.app.injections.base_logger import LoggingFunction
from pypads.injections.analysis.call_tracker import InjectionLoggingEnv
from pypads.utils.util import is_package_available

added_autologs = set()
mlflow_autolog_fns = {}
mlflow_autolog_callbacks = []


def _to_patch_id(patch):
    return str(patch.desitination)


def fake_gorilla_apply(patch):
    if patch.name not in mlflow_autolog_fns:
        mlflow_autolog_fns[patch.name] = {}
    mlflow_autolog_fns[patch.name][patch.destination] = patch


# For now only take last added callback
def fake_gorilla_get_original_attribute(clz, fn_name):
    return mlflow_autolog_callbacks.pop()


gorilla.apply = fake_gorilla_apply
gorilla.get_original_attribute = fake_gorilla_get_original_attribute


# Could also be a normal function right now
class MlflowAutologger(LoggingFunction):
    """
    MlflowAutologger is the intergration of the mlflow autologging functionalities into PyPads tracking system.

    """
    def __init__(self, *args, order=-1, **kwargs):
        super().__init__(*args, order=order, **kwargs)

    @experimental
    def __call_wrapped__(self, ctx, *args, _args, _kwargs, _pypads_autologgers=None, _pypads_env=InjectionLoggingEnv,
                         **kwargs):
        """
            Function used to enable autologgers of mlflow.
        """

        if _pypads_autologgers is None:
            _pypads_autologgers = ["keras", "tensorflow", "xgboost", "gluon", "spark", "lightgbm"]

        if 'tensorflow' in _pypads_autologgers and 'tensorflow' in sys.modules and 'tensorflow' not in added_autologs and is_package_available(
                'tensorflow'):
            added_autologs.add('tensorflow')
            from mlflow import tensorflow
            tensorflow.autolog()

        if 'keras' in _pypads_autologgers and 'keras' in sys.modules and 'keras' not in added_autologs and is_package_available(
                'keras'):
            added_autologs.add('keras')
            from mlflow import keras
            keras.autolog()

        if 'xgboost' in _pypads_autologgers and 'xgboost' in sys.modules and 'xgboost' not in added_autologs and is_package_available(
                'xgboost'):
            added_autologs.add('xgboost')
            from mlflow import xgboost
            xgboost.autolog()

        if 'gluon' in _pypads_autologgers and 'gluon' in sys.modules and 'gluon' not in added_autologs and is_package_available(
                'gluon'):
            added_autologs.add('gluon')
            from mlflow import gluon
            gluon.autolog()

        if 'spark' in _pypads_autologgers and 'spark' in sys.modules and 'spark' not in added_autologs and is_package_available(
                'pyspark'):
            added_autologs.add('spark')
            from mlflow import spark
            spark.autolog()

        if 'lightgbm' in _pypads_autologgers and 'lightgbm' in sys.modules and 'lightgbm' not in added_autologs and is_package_available(
                'lightgbm'):
            added_autologs.add('lightgbm')
            from mlflow import lightgbm
            lightgbm.autolog()

        # If the function is to be logged call the related mlflow autolog function which would have
        #  been applied via gorilla
        if _pypads_env.call.call_id.wrappee.__name__ in mlflow_autolog_fns:
            for destination, patch in mlflow_autolog_fns[_pypads_env.call.call_id.wrappee.__name__].items():
                if destination == _pypads_env.call.call_id.context.container or issubclass(
                        _pypads_env.call.call_id.context.container, destination):
                    from pypads.importext.wrapping.base_wrapper import Context
                    # Jump directly to the original function
                    mlflow_autolog_callbacks.append(Context(destination).original(getattr(destination, patch.name)))
                    return patch.obj(ctx, *_args, **_kwargs)
        return _pypads_env.callback(*_args, **_kwargs)

# # Override mlflow because of: Using functools.wraps unfortunately breaks with inspect.getargspec(fn) of mlflow
# def log_fn_args_as_params(fn, args, kwargs, unlogged=[]):  # pylint: disable=W0102
#     """
#     Log parameters explicitly passed to a function.
#     :param fn: function whose parameters are to be logged
#     :param args: arguments explicitly passed into fn
#     :param kwargs: kwargs explicitly passed into fn
#     :param unlogged: parameters not to be logged
#     :return: None
#     """
#     # all_default_values has length n, corresponding to values of the
#     # last n elements in all_param_names
#     import inspect
#     from mlflow.utils.autologging_utils import try_mlflow_log
#     all_param_names, _, _, all_default_values, _, _, _ = inspect.getfullargspec(fn)  # pylint: disable=W1505
#
#     # Checking if default values are present for logging. Known bug that getargspec will return an
#     # empty argspec for certain functions, despite the functions having an argspec.
#     if all_default_values is not None and len(all_default_values) > 0:
#         # Logging the default arguments not passed by the user
#         from mlflow.utils.autologging_utils import get_unspecified_default_args
#         defaults = get_unspecified_default_args(args, kwargs, all_param_names, all_default_values)
#
#         for name in [name for name in defaults.keys() if name in unlogged]:
#             del defaults[name]
#         try_mlflow_log(mlflow.log_params, defaults)
#
#     # Logging the arguments passed by the user
#     args_dict = dict((param_name, param_val) for param_name, param_val
#                      in zip(all_param_names[:len(args)], args)
#                      if param_name not in unlogged)
#     if len(args_dict.keys()) > 0:
#         try_mlflow_log(mlflow.log_params, args_dict)
#
#     # Logging the kwargs passed by the user
#     for param_name in kwargs:
#         if param_name not in unlogged:
#             try_mlflow_log(mlflow.log_param, param_name, kwargs[param_name])
#
#
# from mlflow.utils import autologging_utils
# autologging_utils.log_fn_args_as_params = log_fn_args_as_params
