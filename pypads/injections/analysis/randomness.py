import random
from logging import warning
from padrepads.util import _is_package_available

# Logging

def log_random_seed(key):
    from pypads.app.base import PyPads
    from pypads.app.pypads import get_current_pads
    pads: PyPads = get_current_pads()

    # Get seed information from cache
    if pads.cache.run_exists(key):
        # TODO if tag already exists (set called multiple times) we need to handle that (save seed per function run?)
        pads.api.set_tag("pypads." + key, pads.cache.run_get(key))
    else:
        warning("Can't log seed produced by seed generator. You have to enable ")


# --- random seed ---
original_random = random.seed


def random_seed(seed):
    try:
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        pads.cache.run_add("random.seed", seed)
        log_random_seed("random.seed")
        return original_random(seed)
    except Exception as e:
        Warning("Tracker failed to log the set seed because %s" % str(e))
        return original_random(seed)


random.seed = random_seed

# --- numpy seed ---
# noinspection PyPackageRequirements,PyUnresolvedReferences
import numpy

original_numpy = numpy.random.seed


def numpy_seed(seed):
    try:
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        pads.cache.run_add("numpy.random.seed", seed)
        log_random_seed("numpy.random.seed")
        return original_numpy(seed)
    except Exception as e:
        Warning("Tracker failed to log the set seed because %s" % str(e))
        return original_numpy(seed)


numpy.random.seed = numpy_seed

# --- pytorch seed ---
if _is_package_available("torch"):
    # noinspection PyPackageRequirements,PyUnresolvedReferences
    import torch

    original_torch = torch.manual_seed


    def torch_seed(seed):
        try:
            from pypads.app.pypads import get_current_pads
            pads = get_current_pads()
            pads.cache.run_add("torch.seed", seed)
            log_random_seed("torch.seed")
            return original_torch(seed)
        except Exception as e:
            Warning("Tracker failed to log the set seed because %s" % str(e))
            return original_torch(seed)


    torch.manual_seed = torch_seed

    if torch.cuda.is_available():
        original_torch_cuda = torch.cuda.manual_seed_all


        def torch_cuda_seed(seed):
            try:
                from pypads.app.pypads import get_current_pads
                pads = get_current_pads()
                pads.cache.run_add("torch.cuda.seed", seed)
                return original_torch_cuda(seed)
            except Exception as e:
                Warning("Tracker failed to log the set seed because %s" % str(e))
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
    if _is_package_available("torch"):
        # noinspection PyPackageRequirements,PyUnresolvedReferences
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
