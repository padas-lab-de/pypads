import sys

from pypads.app.env import LoggerEnv
from pypads.app.injections.run_loggers import RunSetup
from pypads.utils.util import is_package_available

added_auto_logs = set()


class MlFlowAutoRSF(RunSetup):

    def _call(self, *args, _pypads_env: LoggerEnv, _pypads_autologgers=None, _logger_call, _logger_output, **kwargs):
        if _pypads_autologgers is None:
            _pypads_autologgers = ["keras", "tensorflow", "xgboost", "gluon", "spark", "lightgbm", "sklearn"]

        if 'tensorflow' in _pypads_autologgers and 'tensorflow' in sys.modules and 'tensorflow' not in added_auto_logs \
                and is_package_available('tensorflow'):
            added_auto_logs.add('tensorflow')
            from mlflow import tensorflow
            tensorflow.autolog()

        if 'keras' in _pypads_autologgers and 'keras' in sys.modules and 'keras' not in added_auto_logs \
                and is_package_available('keras'):
            added_auto_logs.add('keras')
            from mlflow import keras
            keras.autolog()

        if 'xgboost' in _pypads_autologgers and 'xgboost' in sys.modules and 'xgboost' not in added_auto_logs \
                and is_package_available('xgboost'):
            added_auto_logs.add('xgboost')
            from mlflow import xgboost
            xgboost.autolog()

        if 'gluon' in _pypads_autologgers and 'gluon' in sys.modules and 'gluon' not in added_auto_logs \
                and is_package_available('gluon'):
            added_auto_logs.add('gluon')
            from mlflow import gluon
            gluon.autolog()

        if 'spark' in _pypads_autologgers and 'spark' in sys.modules and 'spark' not in added_auto_logs \
                and is_package_available('pyspark'):
            added_auto_logs.add('spark')
            from mlflow import spark
            spark.autolog()

        if 'lightgbm' in _pypads_autologgers and 'lightgbm' in sys.modules and 'lightgbm' not in added_auto_logs \
                and is_package_available('lightgbm'):
            added_auto_logs.add('lightgbm')
            from mlflow import lightgbm
            lightgbm.autolog()

        if 'sklearn' in _pypads_autologgers and 'sklearn' in sys.modules and 'sklearn' not in added_auto_logs \
                and is_package_available('sklearn'):
            added_auto_logs.add('sklearn')
            from mlflow import sklearn
            sklearn.autolog()

# added_auto_logs = set()
# mlflow_auto_log_fns = {}
# mlflow_auto_log_callbacks = []
#
#
# def _to_patch_id(patch):
#     return str(patch.desitination)
#
#
# def fake_gorilla_apply(patch):
#     if patch.name not in mlflow_auto_log_fns:
#         mlflow_auto_log_fns[patch.name] = {}
#     mlflow_auto_log_fns[patch.name][patch.destination] = patch
#
#
# # For now only take last added callback
# def fake_gorilla_get_original_attribute(clz, fn_name):
#     return mlflow_auto_log_callbacks.pop()
#
#
# gorilla.apply = fake_gorilla_apply
# gorilla.get_original_attribute = fake_gorilla_get_original_attribute
#
#
# # Could also be a normal function right now
# class MlFlowAutoLogger(InjectionLogger):
#     """
#     Mlflow Auto logger is a simple proof of concept integration of the mlflow auto logging functionality into PyPads
#     tracking system. When using this tracking one just produces the output defined by mlflow in an mlflow way.
#     Using this auto logger functionality only saves you the call of mlflow.[lib].auto_log(). No provenance information
#     is stored right now.
#     """
#
#     def __init__(self, *args, order=-1, **kwargs):
#         super().__init__(*args, order=order, **kwargs)
#
#     @experimental
#     def __call_wrapped__(self, ctx, *args, _args, _kwargs, _pypads_autologgers=None, _pypads_env=InjectionLoggerEnv,
#                          **kwargs):
#         """
#             Function used to enable autologgers of mlflow.
#         """
#
#         if _pypads_autologgers is None:
#             _pypads_autologgers = ["keras", "tensorflow", "xgboost", "gluon", "spark", "lightgbm", "sklearn"]
#
#         if 'tensorflow' in _pypads_autologgers and 'tensorflow' in sys.modules and 'tensorflow' not in added_auto_logs \
#                 and is_package_available('tensorflow'):
#             added_auto_logs.add('tensorflow')
#             from mlflow import tensorflow
#             tensorflow.autolog()
#
#         if 'keras' in _pypads_autologgers and 'keras' in sys.modules and 'keras' not in added_auto_logs \
#                 and is_package_available('keras'):
#             added_auto_logs.add('keras')
#             from mlflow import keras
#             keras.autolog()
#
#         if 'xgboost' in _pypads_autologgers and 'xgboost' in sys.modules and 'xgboost' not in added_auto_logs \
#                 and is_package_available('xgboost'):
#             added_auto_logs.add('xgboost')
#             from mlflow import xgboost
#             xgboost.autolog()
#
#         if 'gluon' in _pypads_autologgers and 'gluon' in sys.modules and 'gluon' not in added_auto_logs \
#                 and is_package_available('gluon'):
#             added_auto_logs.add('gluon')
#             from mlflow import gluon
#             gluon.autolog()
#
#         if 'spark' in _pypads_autologgers and 'spark' in sys.modules and 'spark' not in added_auto_logs \
#                 and is_package_available('pyspark'):
#             added_auto_logs.add('spark')
#             from mlflow import spark
#             spark.autolog()
#
#         if 'lightgbm' in _pypads_autologgers and 'lightgbm' in sys.modules and 'lightgbm' not in added_auto_logs \
#                 and is_package_available('lightgbm'):
#             added_auto_logs.add('lightgbm')
#             from mlflow import lightgbm
#             lightgbm.autolog()
#
#         if 'sklearn' in _pypads_autologgers and 'sklearn' in sys.modules and 'sklearn' not in added_auto_logs \
#                 and is_package_available('sklearn'):
#             added_auto_logs.add('sklearn')
#             from mlflow import sklearn
#             sklearn.autolog()
#
#         # If the function is to be logged call the related mlflow autolog function which would have
#         #  been applied via gorilla
#         if _pypads_env.call.call_id.wrappee.__name__ in mlflow_auto_log_fns:
#             for destination, patch in mlflow_auto_log_fns[_pypads_env.call.call_id.wrappee.__name__].items():
#                 if destination == _pypads_env.call.call_id.context.container or issubclass(
#                         _pypads_env.call.call_id.context.container, destination):
#                     from pypads.importext.wrapping.base_wrapper import Context
#                     # Jump directly to the original function
#                     mlflow_auto_log_callbacks.append(Context(destination).original(getattr(destination, patch.name)))
#
#                     def fn(*args, **kwargs):
#                         return patch.obj(ctx, *args, **kwargs)
#
#                     return OriginalExecutor(fn=fn)(*_args, **_kwargs)
#         return OriginalExecutor(fn=_pypads_env.callback)(*_args, **_kwargs)
#
