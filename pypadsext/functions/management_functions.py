import random

from pypads.base import get_current_pads

from pypadsext.util import _is_package_available

# --- random seed ---
original_random = random.seed


def random_seed(seed):
    pads = get_current_pads()
    pads.cache.run_add("random.seed", seed)
    return original_random(seed)


random.seed = random_seed

# --- numpy seed ---
# noinspection PyPackageRequirements,PyUnresolvedReferences
import numpy

original_numpy = numpy.random.seed


def numpy_seed(seed):
    pads = get_current_pads()
    pads.cache.run_add("numpy.random.seed", seed)
    return original_numpy(seed)


numpy.random.seed = numpy_seed

# --- pytorch seed ---
if _is_package_available("pytorch"):
    # noinspection PyPackageRequirements,PyUnresolvedReferences
    import torch

    original_torch = torch.manual_seed


    def torch_seed(seed):
        pads = get_current_pads()
        pads.cache.run_add("torch.seed", seed)
        return original_torch(seed)


    torch.manual_seed = torch_seed

    if torch.cuda.is_available():
        original_torch_cuda = torch.cuda.manual_seed_all


        def torch_cuda_seed(seed):
            pads = get_current_pads()
            pads.cache.run_add("torch.cuda.seed", seed)
            return original_torch_cuda(seed)


        torch.cuda.manual_seed_all = torch_cuda_seed


def set_random_seed(seed):
    import random
    global padre_seed
    padre_seed = seed

    # --- set random seed ---
    random.seed(seed)

    # --- set numpy seed ---

    numpy.random.seed(seed)
    # global seeds for numpy seem to not work with RandomState()

    # --- set pytorch seed ---
    if _is_package_available("pytorch"):
        # noinspection PyPackageRequirements,PyUnresolvedReferences
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
