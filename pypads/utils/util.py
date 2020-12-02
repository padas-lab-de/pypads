import functools
import hashlib
import inspect
import operator
import os
import threading
from functools import reduce
from typing import Tuple

import mlflow
import pkg_resources

from pypads import logger
from pypads.app.misc.caches import Cache
from pypads.exceptions import UninitializedTrackerException


def get_class_that_defined_method(meth):
    """
    Try to find the class / module which defined given method.
    :param meth: Method for which we search an origin.
    :return:
    """
    if inspect.ismethod(meth):
        for cls in inspect.getmro(meth.__self__.__class__):
            if cls.__dict__.get(meth.__name__) is meth:
                return cls
        meth = meth.__func__  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0], None)
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)  # handle special descriptor objects


def dict_merge(*dicts, str_to_set=False):
    """
    Simple merge of dicts
    :param str_to_set: Merge multiple strings to a set
    :param dicts:
    :return:
    """
    merged = {}
    for d in dicts:
        if isinstance(d, dict):
            for key, value in d.items():
                if isinstance(value, str) and str_to_set:
                    if key not in merged:
                        merged[key] = value
                    else:
                        if not isinstance(merged[key], set):
                            merged[key] = {merged[key]}
                        merged[key] = merged[key].union({value})
                        if len(merged[key]) == 1:
                            merged[key] = merged[key].pop()
                elif isinstance(value, set):
                    node = merged.setdefault(key, set())
                    if not isinstance(node, set):
                        merged[key] = {node}
                    merged[key] = merged[key].union(value)
                elif isinstance(value, list):
                    node = merged.setdefault(key, [])
                    if not isinstance(node, list):
                        merged[key] = [node]
                    merged[key].extend([e for e in value if e not in merged[key]])
                elif isinstance(value, dict):
                    node = merged.setdefault(key, {})
                    merged[key] = dict_merge(node, value, str_to_set=str_to_set)
                else:
                    merged[key] = value
    return merged


def persistent_hash(to_hash, algorithm=hashlib.md5):
    """
    Produces a hash which is independant of the current runtime (No salt) unlike __hash__()
    :param to_hash:
    :param algorithm:
    :return:
    """

    def add_str(a, b):
        return operator.add(str(persistent_hash(str(a), algorithm)), str(persistent_hash(str(b), algorithm)))

    if isinstance(to_hash, Tuple):
        to_hash = functools.reduce(add_str, to_hash)
    return int(algorithm(to_hash.encode("utf-8")).hexdigest(), 16)


def sizeof_fmt(num, suffix='B'):
    """
    Get the mem / disk size in a human readable way.
    :param num:
    :param suffix:
    :return:
    """
    if num == 0:
        return '0'
    import math
    magnitude = int(math.floor(math.log(num, 1024)))
    val = num / math.pow(1024, magnitude)
    if magnitude > 7:
        return '{:.1f}{}{}'.format(val, 'Yi', suffix)
    return '{:3.1f}{}{}'.format(val, ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z'][magnitude], suffix)


def uri_to_path(uri):
    """
    Convert URI to local filesystem path.
    """
    from six.moves import urllib
    if uri.startswith("file:"):
        path = urllib.parse.urlparse(uri).path
    elif uri.startswith("http:") or uri.startswith("https:"):
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        path = os.path.join(pads.folder, "tmp")
    else:
        path = uri
    return urllib.request.url2pathname(path)


def string_to_int(s):
    """
    Build a int from a given string.
    :param s:
    :return:
    """
    ord3 = lambda x: '%.3d' % ord(x)
    return int(''.join(map(ord3, s)))


def inheritors(clazz):
    """
    Function getting all subclasses of given class.
    :param clazz: Clazz to search for
    :return:
    """
    subclasses = set()
    unseen = [clazz]
    while unseen:
        parent = unseen.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                unseen.append(child)
    return subclasses


def find_package_regex_versions(regex):
    import pkgutil
    import re
    versions = {
        name: find_package_version(name)
        for finder, name, ispkg
        in pkgutil.iter_modules()
        if re.compile(regex).match(name)
    }
    return versions


def is_package_available(name):
    """
    Check if given package is available.
    :param name: Name of the package
    :return:
    """
    import importlib
    try:
        spam_loader = importlib.util.find_spec(name)
    except Exception as e:
        spam_loader = importlib.find_loader(name)
    return spam_loader is not None


def find_package_version(name: str):
    try:
        import sys
        if name in sys.modules:
            base_package = sys.modules[name]
            if hasattr(base_package, "__version__"):
                lib_version = getattr(base_package, "__version__")
                return lib_version
        else:
            lib_version = pkg_resources.get_distribution(name).version
            return lib_version
    except Exception as e:
        logger.debug("Couldn't get version of package {}".format(name))
        return None


def dict_merge_caches(*dicts):
    """
    Merge two dicts. Entries are overwritten if not mergeable. Cache is supported.
    :param dicts: dicts to merge
    :return:
    """
    merged = {}
    for d in dicts:
        if isinstance(d, dict):
            for key, value in d.items():
                if isinstance(value, dict):
                    node = merged.setdefault(key, {})
                    merged[key] = dict_merge(node, value)
                elif isinstance(value, list):
                    node = merged.setdefault(key, [])
                    try:
                        node.extend(value)
                    except AttributeError as e:
                        try:
                            node = [node]
                            node.extend(value)
                        except Exception as e:
                            logger.error("Failed merging dictionaries in dict_merge_caches : {}".format(str(e)))
                    merged[key] = node
                elif isinstance(value, set):
                    s: set = merged.setdefault(key, set())
                    for v in value:
                        if v in s:
                            merged = dict_merge(v, s.pop(v))
                            s.add(merged)
                        else:
                            s.add(v)
                elif isinstance(value, Cache):
                    node = merged.setdefault(key, Cache())
                    merged[key] = value.merge(node)
                else:
                    merged[key] = value
    return merged


def get_from_dict(d: dict, key_list):
    return reduce(operator.getitem, key_list, d)


def set_in_dict(d: dict, key_list, value):
    get_from_dict(d, key_list[:-1])[key_list[-1]] = value


def has_direct_attr(obj, name):
    """
    Check if self has an attribute
    :param obj: object to check
    :param name: name of the attribute
    :return:
    """
    try:
        object.__getattribute__(obj, name)
        return True
    except AttributeError:
        return False


def get_backend_uri():
    try:
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        if pads:
            return pads.uri
    except (ImportError, UninitializedTrackerException):
        pass  # PyPads is not available here the backend uri is not set. Backend_uri has to be provided later on
    return None


def get_experiment_id():
    if mlflow.active_run():
        return mlflow.active_run().info.experiment_id
    return None


def get_experiment_name():
    if mlflow.active_run():
        from pypads.app.pypads import get_current_pads
        pads = get_current_pads()
        return pads.api.active_experiment().name
    return None


def get_run_id():
    if mlflow.active_run():
        return mlflow.active_run().info.run_id
    return None


class PeriodicThread(threading.Thread):
    def __init__(self, *args, sleep=1.0, target=None, _cleanup=None, _atexit=None, **kwargs):
        self._stop_event = threading.Event()
        self.daemon = True
        self._sleep_period = sleep
        super().__init__(*args, target=target, **kwargs)
        self._cleanup = _cleanup or self._cleanup
        self._atexit = _atexit or self._atexit

    def _sigterm(self, signum, frame):
        threading.Thread(target=self._cleanup, name='CleanupThread').start()

    def _cleanup(self):
        pass

    def _atexit(self):
        pass

    def run(self):
        try:
            while not self._stop_event.isSet():
                if self._target:
                    self._target(*self._args, **self._kwargs)
                self._stop_event.wait(self._sleep_period)
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self._target, self._args, self._kwargs

    def join(self, timeout=None):
        """ Stop the thread. """
        self._stop_event.set()
        threading.Thread.join(self, timeout)
