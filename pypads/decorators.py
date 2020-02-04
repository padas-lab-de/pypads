from functools import wraps
from types import GeneratorType
from typing import Tuple


def unpack(kwargs_obj: dict, *args):
    """
    Unpacks a dict object into a tuple. You can pass tuples for setting default values.
    :param kwargs_obj:
    :param args:
    :return:
    """
    empty = object()
    arg_list = []
    for entry in args:
        if isinstance(entry, str):
            arg_list.append(kwargs_obj.get(entry))
        elif isinstance(entry, Tuple):
            key, *rest = entry
            default = empty if len(rest) == 0 else rest[0]
            if default is empty:
                arg_list.append(kwargs_obj.get(key))
            else:
                arg_list.append(kwargs_obj.get(key, default))
        else:
            raise ValueError("Pass a tuple or string not: " + str(entry))
    return tuple(arg_list)


def split_tracking(cache=None):
    if cache is None:
        cache = dict()

    def decorator(f_splitter):
        @wraps(f_splitter)
        def wrapper(*args, **kwargs):
            splits = f_splitter(*args, **kwargs)
            data = unpack(kwargs , "data")
            if isinstance(splits, GeneratorType):
                for num, train_idx, test_idx in splits:
                    cache[str(num)] = {'train_indices': train_idx, 'test_indices': test_idx}
                    yield num, train_idx, test_idx
            else:
                num, train_idx, test_idx = splits
                cache[str(num)] = {'train_indices': train_idx, 'test_indices': test_idx}
                return num, train_idx, test_idx

        return wrapper

    return decorator