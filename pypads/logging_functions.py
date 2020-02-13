import datetime
from logging import warning, info

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


def log_init(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
             **kwargs):
    info("Pypads tracked class " + str(self.__class__) + " initialized.")
    _pypads_callback(*args, **kwargs)


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
                           _pypads_mapped_by.reference + "." + str(id(self)) + "." + get_now() + "." + k + ".txt", v)
    except Exception as e:
        warning("Couldn't use visitor for parameter extraction. " + str(e) + " Omit logging for now.")
        # for i in range(len(args)):
        #    arg = args[i]
        #    try_mlflow_log(mlflow.log_param, _pypads_mapped_by + "." + str(id(self)) + "." + get_now() + ".args." + str(i), str(arg))
        #
        # for (k, v) in kwargs.items():
        #    try_mlflow_log(mlflow.log_param, _pypads_mapped_by + "." + str(id(self)) + "." + get_now() + ".kwargs." + str(k), str(v))

    return result


def autologgers(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
    # TODO employ the in mlflow already defined autologgers
    # """
    # Example for adding keras autologging code in a simple way
    # :param self:
    # :param args:
    # :param _pypads_wrappe:
    # :param _pypads_context:
    # :param _pypads_mapped_by:
    # :param _pypads_callback:
    # :param kwargs:
    # :return:
    # """
    # import keras
    #
    # class __MLflowKerasCallback(keras.callbacks.Callback):
    #     """
    #     Callback for auto-logging metrics and parameters.
    #     Records available logs after each epoch.
    #     Records model structural information as params when training begins
    #     """
    #
    #     def on_train_begin(self, logs=None):  # pylint: disable=unused-argument
    #         try_mlflow_log(mlflow.log_param, 'num_layers', len(self.model.layers))
    #         try_mlflow_log(mlflow.log_param, 'optimizer_name', type(self.model.optimizer).__name__)
    #         if hasattr(self.model.optimizer, 'lr'):
    #             lr = self.model.optimizer.lr if \
    #                 type(self.model.optimizer.lr) is float \
    #                 else keras.backend.eval(self.model.optimizer.lr)
    #             try_mlflow_log(mlflow.log_param, 'learning_rate', lr)
    #         if hasattr(self.model.optimizer, 'epsilon'):
    #             epsilon = self.model.optimizer.epsilon if \
    #                 type(self.model.optimizer.epsilon) is float \
    #                 else keras.backend.eval(self.model.optimizer.epsilon)
    #             try_mlflow_log(mlflow.log_param, 'epsilon', epsilon)
    #
    #         sum_list = []
    #         self.model.summary(print_fn=sum_list.append)
    #         summary = '\n'.join(sum_list)
    #         try_mlflow_log(mlflow.set_tag, 'model_summary', summary)
    #
    #         import tempfile
    #         tempdir = tempfile.mkdtemp()
    #         try:
    #             import os
    #             summary_file = os.path.join(tempdir, "model_summary.txt")
    #             with open(summary_file, 'w') as f:
    #                 f.write(summary)
    #             try_mlflow_log(mlflow.log_artifact, local_path=summary_file)
    #         finally:
    #             import shutil
    #             shutil.rmtree(tempdir)
    #
    #     def on_epoch_end(self, epoch, logs=None):
    #         if not logs:
    #             return
    #         try_mlflow_log(mlflow.log_metrics, logs, step=epoch)
    #
    #     def on_train_end(self, logs=None):
    #         from mlflow.keras import log_model
    #         try_mlflow_log(log_model, self.model, artifact_path='model')
    #
    # def _early_stop_check(callbacks):
    #     from distutils.version import LooseVersion
    #     if LooseVersion(keras.__version__) < LooseVersion('2.3.0'):
    #         es_callback = keras.callbacks.EarlyStopping
    #     else:
    #         es_callback = keras.callbacks.callbacks.EarlyStopping
    #     for callback in callbacks:
    #         if isinstance(callback, es_callback):
    #             return callback
    #     return None
    #
    # def _log_early_stop_callback_params(callback):
    #     if callback:
    #         try:
    #             earlystopping_params = {'monitor': callback.monitor,
    #                                     'min_delta': callback.min_delta,
    #                                     'patience': callback.patience,
    #                                     'baseline': callback.baseline,
    #                                     'restore_best_weights': callback.restore_best_weights}
    #             try_mlflow_log(mlflow.log_params, earlystopping_params)
    #         except Exception:  # pylint: disable=W0703
    #             return
    #
    # def _get_early_stop_callback_attrs(callback):
    #     try:
    #         return callback.stopped_epoch, callback.restore_best_weights, callback.patience
    #     except Exception:  # pylint: disable=W0703
    #         return None
    #
    # def _log_early_stop_callback_metrics(callback, history):
    #     if callback:
    #         callback_attrs = _get_early_stop_callback_attrs(callback)
    #         if callback_attrs is None:
    #             return
    #         stopped_epoch, restore_best_weights, patience = callback_attrs
    #         try_mlflow_log(mlflow.log_metric, 'stopped_epoch', stopped_epoch)
    #         # Weights are restored only if early stopping occurs
    #         if stopped_epoch != 0 and restore_best_weights:
    #             restored_epoch = stopped_epoch - max(1, patience)
    #             try_mlflow_log(mlflow.log_metric, 'restored_epoch', restored_epoch)
    #             restored_metrics = {key: history.history[key][restored_epoch]
    #                                 for key in history.history.keys()}
    #             # Checking that a metric history exists
    #             metric_key = next(iter(history.history), None)
    #             if metric_key is not None:
    #                 last_epoch = len(history.history[metric_key])
    #                 try_mlflow_log(mlflow.log_metrics, restored_metrics, step=last_epoch)
    #
    # def _run_and_log_function(self, original, args, kwargs, unlogged_params, callback_arg_index):
    #     if not mlflow.active_run():
    #         try_mlflow_log(mlflow.start_run)
    #         auto_end_run = True
    #     else:
    #         auto_end_run = False
    #
    #     log_fn_args_as_params(original, args, kwargs, unlogged_params)
    #     early_stop_callback = None
    #
    #     # Checking if the 'callback' argument of the function is set
    #     if len(args) > callback_arg_index:
    #         tmp_list = list(args)
    #         if list(args)[callback_arg_index] is None:
    #             tmp_list[callback_arg_index] = [__MLflowKerasCallback()]
    #         else:
    #             early_stop_callback = _early_stop_check(tmp_list[callback_arg_index])
    #             tmp_list[callback_arg_index] += [__MLflowKerasCallback()]
    #         args = tuple(tmp_list)
    #     elif 'callbacks' in kwargs:
    #         early_stop_callback = _early_stop_check(kwargs['callbacks'])
    #         kwargs['callbacks'] += [__MLflowKerasCallback()]
    #     else:
    #         kwargs['callbacks'] = [__MLflowKerasCallback()]
    #
    #     _log_early_stop_callback_params(early_stop_callback)
    #
    #     history = original(*args, **kwargs)
    #
    #     _log_early_stop_callback_metrics(early_stop_callback, history)
    #
    #     if auto_end_run:
    #         try_mlflow_log(mlflow.end_run)
    #
    #     return history

    # return _run_and_log_function(self, _pypads_callback, args, kwargs, ['self', 'x', 'y', 'callbacks', 'validation_data', 'verbose'], 5)
    return _pypads_callback(*args, **kwargs)


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
    name = _pypads_context.__name__ + "[" + str(id(self)) + "]." + _pypads_wrappe.__name__ + "(return)"
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
        name = _pypads_context.__name__ + "[" + str(id(self)) + "]." + _pypads_wrappe.__name__ + "(args[" + str(
            i) + "])"
        try_write_artifact(name, arg, write_format)

    for (k, v) in kwargs.items():
        name = _pypads_context.__name__ + "[" + str(id(self)) + "]." + _pypads_wrappe.__name__ + "(kwargs[" + str(
            k) + "])"
        try_write_artifact(name, v, write_format)

    result = _pypads_callback(*args, **kwargs)
    return result


def cpu(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
    import platform
    mlflow.set_tag("pypads.processor", platform.processor())
    return _pypads_callback(*args, **kwargs)


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
        if result is self._pads_wrapped_instance:
            return self
    return result
