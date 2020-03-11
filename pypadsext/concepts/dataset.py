from abc import ABCMeta
from enum import Enum
from typing import Any, Tuple, Callable, Iterable

from pypads.base import tracking_active

from pypadsext.util import _is_package_available


class Types(Enum):
    if _is_package_available('sklearn') and tracking_active:
        from sklearn.utils import Bunch
        bunch = Bunch
    else:
        bunch = "sklearn.utils.Bunch"
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


class Modules(Enum):
    if _is_package_available('sklearn'):
        sklearn = "sklearn.datasets"
    if _is_package_available('keras'):
        keras = "keras.datasets"
    if _is_package_available('torchvision'):
        torch = "torchvision.datasets"


class Crawler:
    __metaclass__ = ABCMeta
    _formats = Types
    _modules = Modules
    _format = None
    _fns = {}

    @classmethod
    def register_fn(cls, _format, fn):
        cls._fns.update({_format: fn})

    def __init__(self, obj: Any, ctx=None, callback: Callable = None, kw=None):
        self._data = obj
        self._callback = callback
        self._ctx = ctx
        self._callback_kw = kw
        self._use_args = False
        self._identify_data_object()

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
            if isinstance(_type.value, str):
                if _type.value in str(type(self._data)):
                    self._format = _type.value
                    break
            else:
                if isinstance(self._data, _type.value):
                    self._format = _type.value
                    break
        self._get_crawler_fn()

    def _check_callback_format(self):
        """
        This function checks the module or the class returning the data object and overwriting the crawler if possible
        :return:
        """
        if self._ctx is not None:
            for key in self._fns:
                if isinstance(key, str) and key in str(self._ctx):
                    self._fn = self._fns.get(key, self._fn)
                    self._format = key
                    break
            self._use_args = True
        else:
            for _ctx in self._modules:
                if _ctx.value == self._callback.__module__ or _ctx.value in self._callback.__module__ or self._callback.__module__ in _ctx.value:
                    self._format = _ctx.value
                    self._fn = self._fns.get(_ctx.value, self._fn)
                    self._use_args = True
                    break

    def _get_crawler_fn(self):
        """
        This maps the object format to the associated crawling function
        :return:
        """
        if self._format:
            self._fn = self._fns.get(self._format, Crawler.default_crawler)
        else:
            self._fn = Crawler.default_crawler
        self._check_callback_format()

    def crawl(self, **kwargs):
        if self._use_args:
            return self._fn(self, *self._callback_kw, **kwargs)
        else:
            return self._fn(self, **kwargs)

    @staticmethod
    def default_crawler(obj, *args, **kwargs):
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
    targets_col = [arg for arg in kwargs if isinstance(arg, Iterable)]
    targets = None
    try:
        targets = obj.data[:, targets_col]
    except Exception as e:
        print(str(e))
    return obj.data, metadata, targets


Crawler.register_fn(Types.ndarray.value, numpy_crawler)


# --- Pandas Dataframe object ---
def dataframe_crawler(obj: Crawler, **kwargs):
    data = obj.data
    metadata = {"type": obj.format, "shape": data.shape, "features": data.columns}
    metadata = {**metadata, **kwargs}
    if "target" in data.columns:
        targets = data[[col for col in data.columns if "target" in col]].values
    else:
        Warning("Target values might be innaccurate.")
        targets = data[[data.columns[-1]]].values
    return data, metadata, targets


Crawler.register_fn(Types.dataframe.value, dataframe_crawler)


# --- Pandas Series object ---
def series_crawler(obj: Crawler, **kwargs):
    data = obj.data
    metadata = {"type": obj.format, "shape": data.shape}
    metadata = {**metadata, **kwargs}
    return data, metadata, None


# --- sklearn dataset object ---
def bunch_crawler(obj: Crawler, **kwargs):
    import numpy as np
    bunch = obj.data
    data = np.concatenate([bunch.get('data'), bunch.get("target").reshape(len(bunch.get("target")), 1)], axis=1)
    metadata = {"type": str(obj.format), "features_names": bunch.get("feature_names"),
                "target_names": list(bunch.get("target_names")), "description": bunch.get("DESCR"), "shape": data.shape}
    metadata = {**metadata, **kwargs}
    return data, metadata, bunch.get("target")


def sklearn_crawler(obj: Crawler, *args, **kwargs):
    import numpy as np
    if True in args:
        X, y = obj.data
        data = np.concatenate([X, y.reshape(len(y), 1)], axis=1)
        metadata = {"type": str(obj.format), "features": X, "shape": (X.shape[0], X.shape[1] + 1)}
        metadata = {**metadata, **kwargs}
        return data, metadata, y
    else:
        return bunch_crawler(obj, **kwargs)


Crawler.register_fn(Types.bunch.value, bunch_crawler)
Crawler.register_fn(Modules.sklearn.value, sklearn_crawler)


# --- TorchVision Dataset object ---
def torch_crawler(obj: Crawler, *args, **kwargs):
    data = obj.data.data.numpy()
    targets = obj.data.targets.numpy()
    metadata = {"format": obj.format, "shape": data.shape, "classes": obj.data.classes,
                "Description": obj.data.__repr__()}
    metadata = {**metadata, **kwargs}
    return data, metadata, targets


if _is_package_available("torch"):
    Crawler.register_fn(Modules.torch.value, torch_crawler)


# --- Keras datasets ---
def keras_crawler(obj: Crawler, *args, **kwargs):
    (X_train, y_train), (X_test, y_test) = obj.data
    import numpy as np
    targets = np.concatenate([y_train, y_test])
    data = np.concatenate([np.concatenate([X_train, X_test]), targets.reshape(len(targets), 1)], axis=1)
    metadata = {"format": obj.format, "shape": data.shape}
    metadata = {**metadata, **kwargs}
    return data, metadata, targets


if _is_package_available("keras"):
    Crawler.register_fn(Modules.keras.value, keras_crawler)


# --- networkx graph object ---
def graph_crawler(obj: Crawler, **kwargs):
    graph = obj.data
    metadata = {"type": str(obj.format), "shape": (graph.number_of_edges(), graph.number_of_nodes())}
    metadata = {**metadata, **kwargs}
    return graph, metadata, None


Crawler.register_fn(Types.graph.value, graph_crawler)
