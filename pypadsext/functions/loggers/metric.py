import mlflow
from mlflow.utils.autologging_utils import try_mlflow_log
from pypads.functions.analysis.call_tracker import LoggingEnv
from pypads.functions.loggers.metric import Metric

from pypadsext.util import _is_package_available


class Metric_torch(Metric):
    """
    Function logging wrapped metrics of PyTroch
    """

    def __post__(self, ctx, *args, _pypads_artifact_fallback=False, _pypads_env: LoggingEnv, _pypads_result, **kwargs):
        """

        :param ctx:
        :param args:
        :param _pypads_artifact_fallback: Write to artifact if metric can not be logged as an double value into mlflow
        :param _pypads_result:
        :param kwargs:
        :return:
        """
        result = _pypads_result

        if _is_package_available("torch"):

            if result is not None:
                from torch import Tensor
                if isinstance(result, Tensor):
                    super().__post__(ctx, *args, _pypads_artifact_fallback=_pypads_artifact_fallback,
                                     _pypads_result=result.item(), **kwargs)
                else:
                    from torch.optim.optimizer import Optimizer
                    if isinstance(ctx, Optimizer):
                        # Logging the gradient of the weigths after the optimizer step
                        param_groups = ctx.param_groups
                        for group in param_groups:
                            weights_by_layer = group.get('params', None)
                            if weights_by_layer and isinstance(weights_by_layer, list):
                                for layer, weights in enumerate(weights_by_layer):
                                    try_mlflow_log(mlflow.log_metric,
                                                   _pypads_env.call.call_id.context.container.__name__+ ".Layer_" + str(
                                                       layer) + "_MEAN_GRADIENT.txt",
                                                   weights.grad.mean().item())
