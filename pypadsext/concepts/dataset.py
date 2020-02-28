from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Any, Tuple, Callable

from pypadsext.util import _is_package_available


class Types(Enum):
    if _is_package_available('sklearn'):
        from sklearn.utils import Bunch
        bunch = Bunch
    else:
        bunch = "sklearn.Bunch"
    if _is_package_available('numpy'):
        from numpy import ndarray
        Ndarray = ndarray
    else:
        ndarray = 'numpy.ndarray'
    if _is_package_available('pandas'):
        from pandas import DataFrame, Series
        dataframe = DataFrame
        series = Series
    else:
        dataframe = 'pandas.DataFrame'
        series = 'pandas.Series'
    if _is_package_available('networkx'):
        from networkx import Graph
        graph = Graph
    else:
        graph = 'networkx.Graph'
    dict = dict
    tuple = Tuple


class Crawler:
    __metaclass__ = ABCMeta
    _formats = Types
    _format = None
    _fns = {}

    @classmethod
    def register_fn(cls, _format, fn):
        cls._fns.update({_format: fn})

    def __init__(self, obj: Any, callbacks: Callable = None):
        self._data = obj
        self._callbacks = callbacks
        self._identify_data_object()
        self._get_crawler_fn()

    @property
    def data(self):
        return self._data

    @property
    def format(self):
        return self._format

    def _identify_data_object(self):
        """
        This function tries to get the type of the object
        :return: class or type of object
        """
        self._format = None
        for _type in self._formats:
            if type(_type.value) == "str":
                if type(self._data) == _type.value:
                    self._format = _type.value
                    break
            else:
                if isinstance(self._data, _type.value):
                    self._format = _type.value
                    break

    def _get_crawler_fn(self):
        if self._format:
            self._fn = self._fns.get(self._format, Crawler.default_crawler)
        else:
            self._fn = Crawler.default_crawler

    def crawl(self, **kwargs):
        return self._fn(self, **kwargs)

    @staticmethod
    def default_crawler(obj, **kwargs):
        metadata = {"type": str(object)}
        metadata = {**metadata, **kwargs}
        if hasattr(obj.data, "shape"):
            try:
                metadata.update({"shape": obj.data.shape})
            except Exception as e:
                print(str(e))
        targets = None
        if hasattr(obj.data, "targets"):
            try:
                targets = obj.data.targets
                metadata.update({"targets": targets})
            except Exception as e:
                print(str(e))
        return obj.data, metadata, targets


# --- Numpy array object ---
def numpy_crawler(obj: Crawler, **kwargs):
    metadata = {"type": str(obj.format), "shape": obj.data.shape}
    metadata = {**metadata, **kwargs}
    return obj.data, metadata, None


Crawler.register_fn(Types.ndarray.value, numpy_crawler)


# --- Pandas Dataframe object ---
def dataframe_crawler(obj : Crawler, **kwargs):
    data = obj.data
    metadata = {"type": obj.format, "shape": data.shape, "features": data.columns}
    metadata = {**metadata, **kwargs}
    targets = None
    if "target" in data.columns:
        targets = data[[col for col in data.columns if "target" in col]]
    return data, metadata, targets


Crawler.register_fn(Types.dataframe.value, dataframe_crawler)


# --- sklearn Bunch object ---
def bunch_crawler(obj: Crawler, **kwargs):
    import numpy as np
    bunch = obj.data
    data = np.concatenate([bunch.get('data'), bunch.get("target").reshape(len(bunch.get("target")), 1)], axis=1)
    metadata = {"type": str(obj.format), "features_names": bunch.get("feature_names"),
                "target_names": list(bunch.get("target_names")), "description": bunch.get("DESCR"), "shape": data.shape}
    metadata = {**metadata, **kwargs}
    return data, metadata, bunch.get("target")


Crawler.register_fn(Types.bunch.value, bunch_crawler)


# --- networkx graph object ---
def graph_crawler(obj, **kwargs):
    graph = obj.data
    metadata = {"type": str(obj.format), "shape": (graph.number_of_edges(), graph.number_of_nodes())}
    metadata = {**metadata, **kwargs}
    return graph, metadata, None


Crawler.register_fn(Types.graph.value, graph_crawler)
