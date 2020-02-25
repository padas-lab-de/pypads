from logging import warning

import mlflow
from pypads.logging_util import try_write_artifact, WriteFormats, all_tags

from pypadsext.concepts.dataset import scrape_data
from pypadsext.concepts.splitter import default_split
from pypadsext.concepts.util import _create_ctx

DATASETS = "datasets"


def random_seed(self, *args, pypads_seed=None, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()

    # Set seed if needed
    if pypads_seed is not None:
        if isinstance(pypads_seed, bool) and pypads_seed:
            import random
            import sys
            pypads_seed = random.randrange(sys.maxsize)
        if isinstance(pypads_seed, int):
            pads.actuators.set_random_seed(pypads_seed)

    # Get seed information from cache
    if pads.cache.run_exists("seed"):
        pads.api.log_param()
    else:
        warning("Can't log seed produced by seed generator. You have to enable ")

    # Run callbacks after seed
    return _pypads_callback(*args, **kwargs)


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
    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()

    result = _pypads_callback(*args, **kwargs)

    # Get additional arguments if given by the user
    _kwargs = dict()
    if pads.cache.run_exists("dataset_kwargs"):
        _kwargs = pads.cache.run_get("dataset_kwargs")

    # Scrape the data object
    data, metadata, targets = scrape_data(result, **_kwargs)
    pads.cache.run_add("data", data)
    pads.cache.run_add("shape", metadata.get("shape"))
    pads.cache.run_add("targets", metadata.get("targets", None))

    # get the current active run
    experiment_run = mlflow.active_run()

    # setting the dataset object name
    if hasattr(result, "name"):
        ds_name = result.name
    elif pads.cache.run_exists("dataset_name") and pads.cache.run_get("dataset_name") is not None:
        ds_name = pads.cache.run_get("dataset_name")
    else:
        ds_name = _pypads_wrappe.__name__

    # Look for metadata information given by the user when using the decorators
    if pads.cache.run_exists("dataset_meta"):
        metadata = {**metadata, **pads.cache.run_get("dataset_meta")}

    # get the repo or create new where datasets are stored
    repo = mlflow.get_experiment_by_name(DATASETS)
    if repo is None:
        repo = mlflow.get_experiment(mlflow.create_experiment(DATASETS))

    # add data set if it is not already existing
    if not any(t["pypads.name"] == ds_name for t in all_tags(repo.experiment_id)):
        with pads.api.intermediate_run(experiment_id=repo.experiment_id) as run:
            dataset_id = run.info.run_id

            pads.cache.run_add("dataset_id", dataset_id, experiment_run.info.run_id)
            mlflow.set_tag("pypads.name", ds_name)
            name = _pypads_context.__name__ + "[" + str(id(result)) + "]." + ds_name + ".data"
            try_write_artifact(name, data, write_format)

            name = _pypads_context.__name__ + "[" + str(id(result)) + "]." + ds_name + ".metadata"
            try_write_artifact(name, metadata, WriteFormats.text)
        mlflow.set_tag("pypads.datasetID", dataset_id)
    return result


def predictions(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback,
                write_format=WriteFormats.text,
                **kwargs):
    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()

    result = _pypads_callback(*args, **kwargs)

    # check if there exists information of the current split
    num = 0
    split_info = None
    if pads.cache.run_exists("current_split"):
        num = pads.cache.run_get("current_split")
    if pads.cache.run_exists(num):
        split_info = pads.cache.run_get(num)

    # check if the estimator computes decision scores
    probabilities = None
    if hasattr(self, "predict_proba") or hasattr(self, "_predict_proba"):
        probabilities = self.predict_proba(*args, **kwargs)

    # depending on available info log the predictions
    if not split_info:
        Warning("No split information were found in cache of the current run, "
                "if individual decision tracking is need, try to decorate you splitter")
        pads.cache.run_add(num, {'predictions': {str(i): {'predicted': result[i]}} for i in range(len(result))})
        if probabilities is not None:
            for i in pads.cache.run_get(num).get('predictions').keys():
                pads.cache.run_get(num).get('predictions').get(str(i)).update(
                    {'probabilities': probabilities[i]})
    else:
        for i, sample in enumerate(split_info.get('test_indices')):
            pads.cache.run_get(num).get('predictions').get(str(sample)).update({'predicted': result[i]})

        if probabilities is not None:
            for i, sample in enumerate(split_info.get('test_indices')):
                pads.cache.run_get(num).get('predictions').get(str(sample)).update(
                    {'probabilities': probabilities[i]})

    name = _pypads_context.__name__ + "[" + str(
        id(self)) + "]." + _pypads_wrappe.__name__ + "_results.split_{}".format(num)
    try_write_artifact(name, pads.cache.run_get(num), write_format)

    return result


def split(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()

    use_default = False
    # check if the default splitter is to be used
    if pads.cache.run_exists("default_splitter"):
        use_default = pads.cache.run_get("default_splitter")
    if use_default:
        ctx = _create_ctx(pads.cache.run_cache())
        kwargs = {}
        if pads.cache.run_exists(_pypads_callback.__qualname__):
            kwargs = pads.cache.run_get(_pypads_callback.__qualname__)
        result = default_split(ctx, **kwargs)
    else:
        result = _pypads_callback(*args, **kwargs)


def hyperparameters(self, *args, _pypads_wrappe, _pypads_context, _pypads_mapped_by, _pypads_callback, **kwargs):
    from pypads.base import get_current_pads
    from pypadsext.base import PyPadrePads
    pads: PyPadrePads = get_current_pads()

    def tracer(frame, event, arg):
        if event == 'return':
            params = frame.f_locals.copy()
            pads.cache.run_add(_pypads_callback.__qualname__, params)

    import sys
    # tracer is activated on next call, return or exception
    sys.setprofile(tracer)
    try:
        fn = _pypads_callback
        if hasattr(_pypads_callback, "__wrapped__"):
            fn = _pypads_callback.__wrapped__
        fn(*args, **kwargs)
    finally:
        # deactivate tracer
        sys.setprofile(None)

    result = _pypads_callback(*args, **kwargs)

    # TODO log parameters?
    return result

# def decorator(f_splitter):
#     @wraps(f_splitter)
#     def wrapper(*args, **kwargs):
#         splits = f_splitter(*args, **kwargs)
#         ds_name = self._pypads.run_cache.get("dataset_name", dataset)
#         ds_id = self._pypads.run_cache.get("dataset_id", None)
#         run_id = self._pypads.run.info.run_id
#
#         def log_split(num, train_idx, test_idx, targets=None):
#             self._pypads.run_cache.add(run_id, {
#                 str(num): {'dataset': ds_name, 'dataset_id': ds_id, 'train_indices': train_idx,
#                            'test_indices': test_idx}})
#
#             if targets is not None:
#                 self._pypads.cache.get(run_id).get(str(num)).update(
#                     {'predictions': {str(sample): {'truth': targets[i]} for i, sample in
#                                      enumerate(test_idx)}})
#             else:
#                 warning(
#                     "Your splitter does not provide targets information, Truth values will be missing from "
#                     "the logged predictions")
#             name = 'Split_{}_{}_information.txt'.format(num, _get_now())
#             try_write_artifact(name,
#                                {'dataset': ds_name, 'train_indices': train_idx, 'test_indices': test_idx},
#                                WriteFormats.text)
#             self._pypads.run_cache.get(run_id).update({"curr_split": num})
#
#         if isinstance(splits, GeneratorType):
#             for num, train_idx, test_idx, targets in splits:
#                 log_split(num, train_idx, test_idx, targets=targets)
#                 yield num, train_idx, test_idx
#         else:
#             num, train_idx, test_idx, targets = splits
#             log_split(num, train_idx, test_idx, targets=targets)
#             return num, train_idx, test_idx
#
#     return wrapper
