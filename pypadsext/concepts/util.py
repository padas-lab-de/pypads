import functools
import hashlib
import operator

from typing import Tuple


def _create_ctx(cache):
    ctx = dict()
    if "data" in cache.keys():
        ctx["data"] = cache.get("data")
    if "shape" in cache.keys():
        ctx["shape"] = cache.get("shape")
    if "targets" in cache.keys():
        ctx["targets"] = cache.get("targets")
    return ctx


def persistent_hash(to_hash, algorithm=hashlib.md5):
    def add_str(a, b):
        return operator.add(str(persistent_hash(str(a), algorithm)), str(persistent_hash(str(b), algorithm)))

    if isinstance(to_hash, Tuple):
        to_hash = functools.reduce(add_str, to_hash)
    return int(algorithm(to_hash.encode("utf-8")).hexdigest(), 16)


def _split_output_inv(result, fn=None):
    # function that looks into the output of the custom splitter
    split_info = dict()
    indices = True
    if isinstance(result, Tuple) or isinstance(result, list):
        n_output = len(result)
        for a in result:
            for row in a:
                if isinstance(row, list):
                    indices = False
                    break

        if n_output > 3:
            if indices:
                Warning('The splitter function return values are ambiguous. Logging....')
                split_info.update({'output_{}'.format(i): a for i, a in enumerate(result)})
                # Todo log the output anyway
            else:
                # TODO log Xtrain, X_test, y_train, y_test if sklearn splitter
                if "sklearn" in fn.__module__:
                    split_info.update({'Xtrain': result[0], 'Xtest': result[1], 'ytrain': result[2],
                                       'ytest': result[3]})
        else:
            if indices:
                names = ['train', 'test', 'val']
                i = 0
                while i < n_output:
                    split_info[names[i]] = result[i]
                    i += 1
            else:
                Warning("Invalid output of the splitter. Logging...")
                split_info.update({'output_{}'.format(i): a for i, a in enumerate(result)})
    else:
        Warning("The splitter has a single output. Logging...")
        split_info.update({'output': result})
    return split_info
