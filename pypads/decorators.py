import os
import tempfile

import mlflow
from boltons.funcutils import wraps

from pypads.base import mlf

DATASETS = "datasets"
TMP = os.path.join(os.path.expanduser("~") + "/.pypads_tmp")

if not os.path.isdir(TMP):
    os.mkdir(TMP)


def dataset(*args, name=None, **kwargs):
    def dataset_decorator(f_create_dataset):
        @wraps(f_create_dataset)
        def wrap_dataset(*args, **kwargs):
            return f_create_dataset(*args, **kwargs)

        dataset = wrap_dataset()

        with tempfile.NamedTemporaryFile(dir=TMP) as fp:
            fp.write(str(dataset["data"]).encode())
            fp.seek(0)

            mlf.get_experiment_by_name()
            mlf.search_runs()

            # get default datasets experiment holding all datasets in form of runs
            # todo it may be better to hold an experiment for each dataset and runs for different versions of the same dataset
            repo = mlf.get_experiment_by_name(DATASETS)
            if repo is None:
                repo = mlf.get_experiment(mlf.create_experiment(DATASETS))

            # extract all tags of runs by experiment id
            def all_tags(experiment_id):
                ds_infos = mlf.list_run_infos(experiment_id)
                for i in ds_infos:
                    yield mlf.get_run(i.run_id).data.tags

            # add data set if it is not already existing
            if not any(t["name"] == dataset["name"] for t in all_tags(repo.experiment_id)):
                run = mlf.create_run(repo.experiment_id, tags={"name": dataset["name"]})
                mlf.log_artifact(run_id=run.info.run_id, local_path=os.path.join(TMP, fp.name), artifact_path="data")
                mlf.set_terminated(run_id=run.info.run_id)

    return dataset_decorator
