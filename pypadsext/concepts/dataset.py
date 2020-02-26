from enum import Enum

from sklearn.utils import Bunch

from pypadsext.util import is_package_available


class Data:

    class Types(Enum):
        bunch = Bunch
        if is_package_available('numpy'):
            from numpy import ndarray
            Ndarray = ndarray
        else:
            ndarray = 'numpy.ndarray'
        if is_package_available('pandas'):
            from pandas import DataFrame, Series
            dataframe = DataFrame
            series = Series
        else:
            dataframe = 'pandas.DataFrame'
            series = 'pandas.Series'
        if is_package_available('networkx'):
            from networkx import Graph
            graph = Graph
        else:
            graph = 'networkx.Graph'
        dict = dict


def numpy_crawl(obj,**kwargs):
    metadata = {"type": str(Data.Types.ndarray.value), "shape": obj.shape}
    data = obj
    return data, metadata, None


def dataframe_crawl(obj,**kwargs):
    metadata = {"type": str(Data.Types.dataFrame.value), "shape": obj.shape, "features": obj.columns}
    data = obj
    targets = None
    if "target" in obj.columns:
        targets = data[[col for col in obj.columns if "target" in col]]
    return data, metadata, targets


def bunch_crawl(obj,**kwargs):
    import numpy as np
    data = np.concatenate([obj.get('data'), obj.get("target").reshape(len(obj.get("target")),1)], axis=1)
    metadata = {"type": str(Data.Types.bunch.value), "features_names": obj.get("feature_names"),
                "target_names": list(obj.get("target_names")), "description": obj.get("DESCR"), "shape": data.shape}
    return data, metadata, obj.get("target")


def graph_crawl(obj, **kwargs):
    metadata = {"type": str(Data.Types.graph.value), "shape": (obj.number_of_edges(), obj.number_of_nodes())}
    data = obj
    return data, obj, None


def object_crawl(obj, **kwargs):
    metadata = {"type": str(object)}
    if hasattr(obj, "shape"):
        metadata.update({"shape": obj.shape})
    targets = None
    if hasattr(obj, "targets"):
        targets = obj.targets
        metadata.update({"targets": targets})
    data = obj
    return data, metadata, targets


crawl_fns = {
    str(Data.Types.bunch.value): bunch_crawl,
    str(Data.Types.ndarray.value) : numpy_crawl,
    str(Data.Types.dataframe.value) : dataframe_crawl,
    str(Data.Types.graph.value) : graph_crawl,
    str(object) : object_crawl
}


def _identify_data_object(obj):
    """
    This function would try to get as much information from this object
    :param obj: obj to stip
    :return:
    """
    obj_ctx = None
    for _type in Data.Types:
        if type(_type.value) == "str":
            if type(obj) == _type.value:
                obj_ctx = _type.value
                break
        else:
            if isinstance(obj, _type.value):
                obj_ctx = _type.value
                break
    return obj_ctx


def _scrape_obj(obj, ctx=None, **kwargs):
    """
    Depending on the object type, crawl information from the object
    :param obj:
    :param ctx:
    :return:
    """
    _proxy_fn = crawl_fns[str(ctx)]
    data, metadata, targets = _proxy_fn(obj, **kwargs)
    return data, metadata, targets


def scrape_data(obj, **kwargs):
    ctx = _identify_data_object(obj)
    return _scrape_obj(obj, ctx, **kwargs)


# @wraps(f_create_dataset)
# def wrap_dataset(*args, **kwargs):
#     dataset = f_create_dataset(*args, **kwargs)
#
#     repo = mlflow.get_experiment_by_name(DATASETS)
#     if repo is None:
#         repo = mlflow.get_experiment(mlflow.create_experiment(DATASETS))
#
#     # add data set if it is not already existing
#     if not any(t["name"] == name for t in all_tags(repo.experiment_id)):
#         # stop the current run
#         self.stop_run()
#         run = mlflow.start_run(experiment_id=repo.experiment_id)
#
#         dataset_id = run.info.run_id
#         self.add("dataset_id", dataset_id)
#         self.add("dataset_name", name)
#         mlflow.set_tag("name", name)
#         name_ = f_create_dataset.__qualname__ + "[" + str(id(dataset)) + "]." + name + "_data"
#         if hasattr(dataset, "data"):
#             if hasattr(dataset.data, "__self__") or hasattr(dataset.data, "__func__"):
#                 try_write_artifact(name_, dataset.data(), WriteFormats.pickle)
#                 self.add("data", dataset.data())
#             else:
#                 try_write_artifact(name_, dataset.data, WriteFormats.pickle)
#                 self.add("data", dataset.data)
#         else:
#             try_write_artifact(name_, dataset, WriteFormats.pickle)
#
#         if metadata:
#             name_ = f_create_dataset.__qualname__ + "[" + str(id(dataset)) + "]." + name + "_metadata"
#             try_write_artifact(name_, metadata, WriteFormats.text)
#         elif hasattr(dataset, "metadata"):
#             name_ = f_create_dataset.__qualname__ + "[" + str(id(dataset)) + "]." + name + "_metadata"
#             if hasattr(dataset.metadata, "__self__") or hasattr(dataset.metadata, "__func__"):
#                 try_write_artifact(name_, dataset.metadata(), WriteFormats.text)
#             else:
#                 try_write_artifact(name_, dataset.metadata, WriteFormats.text)
#         self.resume_run()
#         mlflow.set_tag("dataset", dataset_id)
#
#     return dataset
#
# return wrap_dataset