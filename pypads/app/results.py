from abc import ABCMeta
from functools import wraps
from typing import Union

from mlflow.entities import ViewType
from pandas import DataFrame, Series

from pypads.app.misc.extensions import ExtendableMixin, Plugin
from pypads.app.misc.mixins import FunctionHolderMixin
from pypads.model.models import ResultType
from pypads.utils.logging_util import read_artifact, FileFormats

result_plugins = set()
result_set = set()


class Result(FunctionHolderMixin, metaclass=ABCMeta):

    def __init__(self, *args, fn, **kwargs):
        super().__init__(*args, fn=fn, **kwargs)
        result_set.add(self)

    def __call__(self, *args, **kwargs):
        return self.__real_call__(*args, **kwargs)


class IResults(Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(type=Result, *args, **kwargs)
        result_plugins.add(self)

    def _get_meta(self):
        """ Method returning information about where the actuator was defined."""
        return self.__module__

    def _get_methods(self):
        return [method_name for method_name in dir(self) if callable(getattr(object, method_name))]


def result(f):
    """
    Result used to convert a function to a tracked actuator.
    :param f:
    :return:
    """
    result_cmd = Result(fn=f)

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        # self is an instance of the class
        return result_cmd(self, *args, **kwargs)

    return wrapper


class PyPadsResults(IResults):
    def __init__(self):
        super().__init__()

    @property
    def pypads(self):
        from pypads.app.pypads import get_current_pads
        return get_current_pads()

    # --- results management ---
    @result
    def get_run(self, run_id=None):
        run_id = run_id or self.pypads.api.active_run().info.run_id
        return self.pypads.backend.get_run(run_id)

    @result
    def list_experiments(self, view_type: ViewType = ViewType.ALL):
        return self.pypads.backend.list_experiments(view_type)

    @result
    def load_artifact(self, relative_path, run_id=None, read_format: FileFormats = None):
        if not run_id:
            run_id = self.pypads.api.active_run().info.run_id
        return read_artifact(
            self.pypads.backend.download_tmp_artifacts(run_id=run_id, relative_path=relative_path),
            read_format=read_format)

    @result
    def list_run_infos(self, experiment_name=None, experiment_id=None, run_view_type: ViewType = ViewType.ALL):
        if experiment_id is None:
            if experiment_name is not None:
                experiment = self.pypads.backend.get_experiment_by_name(experiment_name)
                experiment_id = experiment.experiment_id
            else:
                raise ValueError("Pass either a name or an id to list run infos.")
        return self.pypads.backend.list_run_infos(experiment_id=experiment_id, run_view_type=run_view_type)

    @result
    def get_metrics(self, experiment_name=None, run_id=None, logger_id=None, output_id=None, tracked_object_id=None,
                    **kwargs):
        return self.list(ResultType.metric, experiment_name=experiment_name, run_id=run_id,
                         logger_id=logger_id, output_id=output_id, tracked_object_id=tracked_object_id,
                         search_dict=kwargs)

    @result
    def get_tags(self, experiment_name=None, run_id=None, logger_id=None, output_id=None, tracked_object_id=None,
                 **kwargs):
        return self.list(ResultType.tag, experiment_name=experiment_name, run_id=run_id,
                         logger_id=logger_id, output_id=output_id, tracked_object_id=tracked_object_id,
                         search_dict=kwargs)

    @result
    def get_parameters(self, experiment_name=None, run_id=None, logger_id=None, output_id=None, tracked_object_id=None,
                       **kwargs):
        return self.list(ResultType.parameter, experiment_name=experiment_name, run_id=run_id,
                         logger_id=logger_id, output_id=output_id, tracked_object_id=tracked_object_id,
                         search_dict=kwargs)

    @result
    def get_artifacts(self, experiment_name=None, run_id=None, logger_id=None, output_id=None, tracked_object_id=None,
                      **kwargs):
        return self.list(ResultType.artifact, experiment_name=experiment_name, run_id=run_id,
                         logger_id=logger_id, output_id=output_id, tracked_object_id=tracked_object_id,
                         search_dict=kwargs)

    def get_tracked_objects(self, experiment_name=None, run_id=None, logger_id=None, output_id=None, **kwargs):
        return self.list(ResultType.tracked_object, experiment_name=experiment_name, run_id=run_id,
                         logger_id=logger_id, output_id=output_id,
                         search_dict=kwargs)

    def get_outputs(self, experiment_name=None, run_id=None, logger_id=None, **kwargs):
        return self.list(ResultType.output, experiment_name=experiment_name, run_id=run_id,
                         logger_id=logger_id, search_dict=kwargs)

    def get(self, uid, storage_type: Union[str, ResultType]):
        return self.pypads.backend.get(uid, storage_type)

    @result
    def list(self, storage_type: Union[str, ResultType], experiment_name=None, experiment_id=None, run_id=None,
             logger_id=None, output_id=None, tracked_object_id=None, search_dict=None):
        """
        Lists data for a given filter.
        :param storage_type: Type to look for.
        :param experiment_name: Filter by experiment name
        :param experiment_id: Filter by experiment id
        :param run_id: Filter by run_id
        :param logger_id: Filter by producing logger id
        :param output_id: Filter by output id
        :param tracked_object_id: Filter by tracked_object_id
        :param search_dict: Additional filters
        :return:
        """
        if search_dict is None:
            search_dict = {}
        if logger_id:
            search_dict = {**search_dict, **{"produced_by": logger_id}}
        if output_id:
            search_dict = {**search_dict, **{"part_of": output_id, "parent_type": ResultType.output}}
        if tracked_object_id:
            search_dict = {**search_dict, **{"part_of": tracked_object_id, "parent_type": ResultType.tracked_object}}
        return self.pypads.backend.list(storage_type=storage_type, experiment_name=experiment_name,
                                        experiment_id=experiment_id, run_id=run_id, search_dict=search_dict)

    @result
    def get_run(self, run_id):
        self.pypads.backend.get_run(run_id=run_id)

    @result
    def get_experiment(self, experiment_name=None, experiment_id=None):
        if experiment_id:
            return self.pypads.backend.get_experiment(experiment_id)
        elif experiment_name:
            return self.pypads.backend.get_experiment_by_name(experiment_name)
        raise ValueError("Pass either a name or id to find a representative experiment.")

    def get_summary(self, experiment_names=None, experiment_ids=None, run_ids=None, search_dict=None, group_by=None):

        def _to_data(column):
            def get_data(val):
                if hasattr(val, "storage_type"):
                    if getattr(val, "storage_type") in [ResultType.parameter, ResultType.metric]:
                        return getattr(val, "data")
                return val

            return column.apply(get_data)

        def _to_tag_data(column):
            def get_data(val):
                return [(name, tag_meta.data) for name, tag_meta in val]

            return column.apply(get_data)

        df = self.get_data_frame(experiment_names=experiment_names, experiment_ids=experiment_ids, run_ids=run_ids,
                                 search_dict=search_dict)
        df = df.apply(lambda x: _to_data(x) if not x.name == "tags" else _to_tag_data(x), axis=0)

        def _group(column):
            def get_data(val):
                return [(name, tag_meta.data) for name, tag_meta in val]

            return column.apply(get_data)

        if group_by is not None:
            pass
            # TODO group by and aggregate other columns
            # df = df.groupby(..., axis=0)

        return df

    @result
    def get_data_frame(self, experiment_names=None, experiment_ids=None, run_ids=None, search_dict=None):
        """
        Returns a pandas data frame containing results of the last runs of the experiment.
        The results contain all parameters and metrics as well as timestamps of the execution and notes about the runs.
        :return:
        """
        # Ids to set
        if experiment_ids is None:
            experiment_ids = set()
        elif isinstance(experiment_ids, str):
            experiment_ids = {experiment_ids}
        elif isinstance(experiment_ids, list):
            experiment_ids = set(experiment_ids)

        # Names to ids
        if experiment_names is not None:
            if isinstance(experiment_names, str):
                experiment_names = {experiment_names}
            for name in experiment_names:
                experiment_ids.update([self.get_experiment(name).experiment_id])

        # Run ids
        if run_ids is not None:
            if isinstance(run_ids, str):
                run_ids = {run_ids}
            elif isinstance(run_ids, list):
                run_ids = set(run_ids)

        df = DataFrame()
        # Add experiments
        for e_id in experiment_ids:

            runs = self.list_run_infos(experiment_id=e_id)
            filtered_runs = [r for r in runs if run_ids is None or r.run_id in run_ids]
            for run_info in filtered_runs:
                run_id = run_info.run_id
                metrics = self.get_metrics(run_id=run_id)
                metrics = {"m_" + m.name: m for m in metrics}
                parameters = self.get_parameters(run_id=run_id)
                parameters = {"p_" + p.name: p for p in parameters}
                tags = self.get_tags(run_id=run_id)
                tags = {"tags": [(t.name, t) for t in tags]}
                exp = {"experiment": e_id}
                run = {"start_time": run_info.start_time, "end_time": run_info.end_time}
                row = {**exp, **run, **metrics, **parameters, **tags}
                index = row.keys()
                data = row.values()
                run_series = Series(data=[v for v in data], index=index, name=run_id)
                df = df.append(run_series)

        return df


class ResultPluginManager(ExtendableMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(plugin_list=result_plugins)


pypads_results = PyPadsResults()


def results():
    """
    Returns classes of
    :return:
    """
    command_list = list(result_set)
    command_list.sort(key=lambda a: str(a))
    return command_list
