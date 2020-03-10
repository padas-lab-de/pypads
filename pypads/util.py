import inspect


def get_class_that_defined_method(meth):
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


def is_package_available(name):
    import importlib
    spam_loader = importlib.util.find_spec(name)
    return spam_loader is not None
