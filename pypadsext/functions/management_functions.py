from pypadsext.util import _is_package_available


def set_random_seed(seed):
    import random
    global padre_seed
    padre_seed = seed
    random.seed(seed)

    # set numpy seed
    import numpy
    numpy.random.seed(seed)
    # global seeds for numpy seem to not work with RandomState()

    # set pytorch seed
    if _is_package_available("pytorch"):
        # noinspection PyPackageRequirements,PyUnresolvedReferences
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
