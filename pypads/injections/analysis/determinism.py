import os

import tensorflow

from pypads import logger
from pypads.utils.util import _is_package_available


def check_determinism():
    from pypads.app.pypads import get_current_pads
    pads = get_current_pads()

    tf_version = tensorflow.version.VERSION
    if tensorflow.match("(1\.(14|15)|2\.0)", tf_version):
        if "TF_USE_CUDNN_AUTOTUNE" in os.environ:
            logger.warning(
                "When using TF auto-tuning of cuDNN convolution algorithms your experiment might"
                " be non-deterministic.")
            pads.api.set_tag("non-determinism", "CUDNN_AUTOTUNE")

        if ("TF_CUDNN_DETERMINISTIC" not in os.environ or (not os.environ["TF_CUDNN_DETERMINISTIC"] and os.environ[
            "TF_CUDNN_DETERMINISTIC"] is not 1)):
            if not _is_package_available("tfdeterminism"):
                logger.warning(
                    "Your experiment might include a gpu-specific sources of non-determinism."
                    " See https://github.com/NVIDIA/tensorflow-determinism")
                pads.api.set_tag("non-determinism",
                                 "TF auto-tuning of cuDNN convolution algorithms (see multi-algo note)")

    # TODO Check for different settings (see ttps://github.com/NVIDIA/tensorflow-determinism)

# def _check_autotuning(self):
#
# def _check_backprop_weight_gradients(self):
#
# def _check_backprop_data_gradients(self):
#
# def _check_cuDNN_maxpooling_backprop(self):
#
# def _check_cuDNN_CTC_loss(self):
#
# def _check_bias_add_backprop(self):
#
# def _check_XLA_reductions_on_GPU(self):
#
# def _check_fused_softmax_cross_entropy_ops_backprop(self):
#     logger.warning("When using TF auto-tuning of cuDNN convolution algorithms your experiment might
#     be non-deterministic.")
