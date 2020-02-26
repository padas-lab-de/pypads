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


def dict_merge(source, destination):
    """
    run me with nosetests --with-doctest file.py

    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> dict_merge(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    https://stackoverflow.com/questions/20656135/python-deep-merge-dictionary-data
    True
    """
    if isinstance(source, dict) and isinstance(destination, dict):
        for key, value in source.items():
            if isinstance(value, dict):
                # get node or create one
                node = destination.setdefault(key, {})
                dict_merge(value, node)
            else:
                destination[key] = value

    return destination
