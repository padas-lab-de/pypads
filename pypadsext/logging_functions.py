import mlflow

from pypads.logging_util import try_write_artifact, WriteFormats, all_tags

# from pypadsext.concepts.dataset import log_data
from pypadsext.concepts.dataset import log_data

DATASETS = "datasets"


def dataset(self, *args, write_format=WriteFormats.pickle, _pypads_wrappe, _pypads_context, _pypads_mapped_by,
            _pypads_callback, **kwargs):
    """
        Function logging the loaded dataset.
        :param self: Wrapper library object
        :param args: Input args to the real library call
        :param _pypads_wrappe: _pypads provided - wrapped library object
        :param _pypads_mapped_by: _pypads provided - wrapped library package
        :param _pypads_item: _pypads provided - wrapped function name
        :param _pypads_fn_stack: _pypads provided - stack of all the next functions to execute
        :param kwargs: Input kwargs to the real library call
        :return:
        """
    result = _pypads_callback(*args, **kwargs)
    data, metadata = log_data(result)
    from pypads.base import get_current_pads
    pads = get_current_pads()

    experiment_run = mlflow.active_run()

    if hasattr(result, "name"):
        ds_name = result.name
    elif pads.cache.run_exists("dataset_name"):
        ds_name = pads.cache.run_get("dataset_name")
    else:
        ds_name = _pypads_wrappe.__name__

    if pads.cache.run_exists("dataset_meta"):
        metadata = {**metadata, **pads.cache.run_get("dataset_meta")}

    repo = mlflow.get_experiment_by_name(DATASETS)
    if repo is None:
        repo = mlflow.get_experiment(mlflow.create_experiment(DATASETS))

    # add data set if it is not already existing
    if not any(t["name"] == ds_name for t in all_tags(repo.experiment_id)):
        with pads.api.intermediate_run(experiment_id=repo.experiment_id) as run:
            dataset_id = run.info.run_id

            pads.cache.run_add("dataset_id", dataset_id, experiment_run.info.run_id)
            mlflow.set_tag("name", ds_name)
            name = _pypads_context.__name__ + "[" + str(id(result)) + "]." + ds_name + ".data"
            try_write_artifact(name, data, write_format)

            name = _pypads_context.__name__ + "[" + str(id(result)) + "]." + ds_name + ".metadata"
            try_write_artifact(name, metadata, WriteFormats.text)
        mlflow.set_tag("dataset", dataset_id)
    return result


def predictions(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
                    write_format=WriteFormats.text,
                    **kwargs):
    result = _pypads_callback(*args, **kwargs)
    from pypads.base import get_current_pads
    pads = get_current_pads()
    run = pads.run_id()
    num = pads.cache.get(run).get("curr_split")
    for i, sample in enumerate(pads.cache.get(run).get(str(num)).get('test_indices')):
        pads.cache.get(run).get(str(num)).get('predictions').get(str(sample)).update({'predicted': result[i]})

    probabilities = None
    if hasattr(self, "predict_proba") or hasattr(self, "_predict_proba"):
        probabilities = self.predict_proba(*args, **kwargs)
    if probabilities is not None:
        for i, sample in enumerate(pads.cache.get(run).get(str(num)).get('test_indices')):
            pads.cache.get(run).get(str(num)).get('predictions').get(str(sample)).update(
                {'probabilities': probabilities[i]})

    name = _pypads_context.__name__ + "[" + str(
        id(self)) + "]." + _pypads_wrappe.__name__ + "_results.split_{}".format(num)
    try_write_artifact(name, pads.cache.get(run).get(str(num)), write_format)

    return result
