import os
from logging import warning

from pypads.functions.analysis.call_tracker import LoggingEnv
from pypads.functions.loggers.base_logger import LoggingFunction
from pypads.logging_util import WriteFormats

from padrepads.concepts.dataset import Crawler
from padrepads.concepts.util import persistent_hash, get_by_tag


class Dataset(LoggingFunction):
    DATASETS = "datasets"
    """
    Function logging the wrapped dataset loader
    """

    def __post__(self, ctx, *args, _pypads_write_format=WriteFormats.pickle, _pypads_env: LoggingEnv, _pypads_result,
                 _args, _kwargs, **kwargs):
        from pypads.base import get_current_pads
        from padrepads.base import PyPadrePads
        pads: PyPadrePads = get_current_pads()

        # if the return object is None, take the object instance ctx
        obj = _pypads_result if _pypads_result else ctx

        # Get additional arguments if given by the user
        _dataset_kwargs = dict()
        if pads.cache.run_exists("dataset_kwargs"):
            _dataset_kwargs = pads.cache.run_get("dataset_kwargs")

        # Scrape the data object
        crawler = Crawler(obj, ctx=_pypads_env.call.call_id.context, callback=_pypads_env.callback, kw=_kwargs)
        data, metadata, targets = crawler.crawl(**_dataset_kwargs)
        pads.cache.run_add("data", data)
        pads.cache.run_add("shape", metadata.get("shape"))
        pads.cache.run_add("targets", targets)

        # get the current active run
        current_run = pads.api.active_run()

        # setting the dataset object name
        if hasattr(obj, "name"):
            ds_name = obj.name
        elif pads.cache.run_exists("dataset_name") and pads.cache.run_get("dataset_name") is not None:
            ds_name = pads.cache.run_get("dataset_name")
        else:
            ds_name = _pypads_env.call.call_id.wrappee.__qualname__

        # Look for metadata information given by the user when using the decorators
        if pads.cache.run_exists("dataset_meta"):
            metadata = {**metadata, **pads.cache.run_get("dataset_meta")}

        # get the name before switching the active run
        name = os.path.join(_pypads_env.call.to_folder(),
                            "data", str(id(_pypads_env.callback)))

        # get the repo or create new where datasets are stored
        repo = pads.mlf.get_experiment_by_name(self.DATASETS)
        if repo is None:
            repo = pads.mlf.get_experiment(pads.mlf.create_experiment(self.DATASETS))

        # add data set if it is not already existing with name and hash check
        try:
            _hash = persistent_hash(str(obj))
        except Exception:
            warning("Could not compute the hash of the dataset object, falling back to dataset name hash...")
            _hash = persistent_hash(str(ds_name))

        _stored = get_by_tag("pypads.dataset.hash", str(_hash), repo.experiment_id)
        if not _stored:
            with pads.api.intermediate_run(experiment_id=repo.experiment_id) as run:
                dataset_id = run.info.run_id

                pads.cache.run_add("dataset_id", dataset_id, current_run.info.run_id)
                pads.api.set_tag("pypads.dataset", ds_name)
                pads.api.set_tag("pypads.dataset.hash", _hash)

                pads.api.log_mem_artifact(name, data, write_format=_pypads_write_format, meta=metadata)

            pads.api.set_tag("pypads.datasetID", dataset_id)
        else:
            # look for the existing dataset and reference it to the active run
            if len(_stored) > 1:
                warning("multiple existing datasets with the same hash!!!")
            else:
                dataset_id = _stored.pop().info.run_id
                pads.api.set_tag("pypads.datasetID", dataset_id)
