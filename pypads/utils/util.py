import inspect

from pypads.app.misc.caches import Cache


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


def dict_merge(*dicts):
    """
    Simple merge of dicts
    :param dicts:
    :return:
    """
    merged = {}
    for d in dicts:
        if isinstance(d, dict):
            for key, value in d.items():
                if isinstance(value, dict):
                    node = merged.setdefault(key, {})
                    merged[key] = dict_merge(node, value)
                else:
                    merged[key] = value
    return merged


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


def local_uri_to_path(uri):
    """
    Convert URI to local filesystem path.
    """
    from six.moves import urllib
    path = urllib.parse.urlparse(uri).path if uri.startswith("file:") else uri
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


def is_package_available(name):
    """
    Check if given package is available.
    :param name: Name of the package
    :return:
    """
    import importlib
    spam_loader = importlib.util.find_spec(name)
    return spam_loader is not None


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
                    merged[key] = node.extend(value)
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
