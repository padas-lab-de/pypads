from typing import Callable

from boltons.funcutils import wraps


# class Attribute(dict):
#
#     def __init__(self, name, measurementLevel=None, unit=None,
#                  description=None, defaultTargetAttribute=False, context=None, index=None, type=None, nullable=True):
#
#         if context is None:
#             context = {}
#         dict.__init__(self, name=name, measurementLevel=measurementLevel,
#                       unit=unit, description=description, defaultTargetAttribute=defaultTargetAttribute,
#                       context=context, index=index, type=type, nullable=nullable)
#
#     @property
#     def name(self):
#         if "name" in self:
#             return self["name"]
#         else:
#             self["name"] = None
#             return None
#
#     @property
#     def index(self):
#         if "index" in self:
#             return self["index"]
#         else:
#             self["index"] = None
#             return None
#
#     @property
#     def measurementLevel(self):
#         if "measurementLevel" in self:
#             return self["measurementLevel"]
#         else:
#             self["measurementLevel"] = ""
#             return self["measurementLevel"]
#
#     @property
#     def unit(self):
#         if "unit" in self:
#             return self["unit"]
#         else:
#             self["unit"] = ""
#             return self["unit"]
#
#     @property
#     def description(self):
#         if "description" in self:
#             return self["description"]
#         else:
#             self["description"] = ""
#             return self["description"]
#
#     @property
#     def defaultTargetAttribute(self):
#         if "defaultTargetAttribute" in self:
#             return self["defaultTargetAttribute"]
#         else:
#             self["defaultTaretAttribute"] = False
#             return False
#
#     @property
#     def context(self):
#         if "context" in self:
#             return self["context"]
#         else:
#             self["context"] = dict()
#             return self["context"]
#
#     def __str__(self):
#         return self.name
#
#     def __repr__(self):
#         if "graph_role" in self.context:
#             return self.name + "(" + self.context["graph_role"] + ")"
#         else:
#             return str(self["name"])


class Dataset:

    def __init__(self, data, features=None, targets=None, attributes=None, **kwargs):
        # Default metadata
        defaults = {"name": "default_name", "version": "1.0", "description": "", "originalSource": "",
                    "type": "http://www.padre-lab.eu/onto/Multivariat", "published": False, "attributes": [],
                    "targets": []}
        self._metadata = {**defaults, **kwargs.pop("metadata", {})}

        self._metadata = {**self._metadata, **{"id": self._metadata.get("name")}}

        self._data = data
        self._features = features
        self._targets = targets
        self._attributes = attributes
        self._shape = None

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def features(self):
        return self._features

    @property
    def targets(self):
        return self._targets

    @property
    def shape(self):
        return self._shape

    def features_fn(self):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                return fn( *args, **kwargs)
            if self._features is None:
                setattr(self, "_features", wrapper())

        return decorator

    def targets_fn(self):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                return fn(*args, **kwargs)
            if self._targets is None:
                setattr(self, "_targets", wrapper())

        return decorator

    def shape_fn(self):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                return fn(*args, **kwargs)
            if self._shape is None:
                setattr(self, "_shape", wrapper())

        return decorator

    def attributes(self):
        return self._attributes
