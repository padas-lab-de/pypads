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

    @result
    def get_summary(self, df=None, group_by=None):
        """
        Produces a summary of given data frame by converting the content to simplified data entries and grouping etc.
        :param df:
        :param group_by:
        :return:
        """

        if df is None:
            df = self.get_experiments_data_frame(experiment_ids=self.pypads.api.active_experiment().experiment_id)

        def _to_data(column):
            def get_data(val):
                if hasattr(val, "storage_type"):
                    if getattr(val, "storage_type") in [ResultType.parameter, ResultType.metric, ResultType.tag]:
                        return getattr(val, "data")
                return val

            return column.apply(get_data)

        df = df.apply(lambda x: _to_data(x), axis=0)

        if group_by is not None:
            df = df.groupby(group_by).std()
            # TODO aggregate columns into val + std deviation
        return df

    def _get_by_dict(self, search_dict):
        if 'storage_type' in search_dict:
            if search_dict['storage_type'] == ResultType.metric.value:
                return self.get_metrics(**search_dict)
            elif search_dict['storage_type'] == ResultType.parameter.value:
                return self.get_parameters(**search_dict)
            elif search_dict['storage_type'] == ResultType.tag.value:
                return self.get_tags(**search_dict)
            elif search_dict['storage_type'] == ResultType.artifact.value:
                return self.get_artifacts(**search_dict)
            elif search_dict['storage_type'] == ResultType.tracked_object.value:
                return self.get_tracked_objects(**search_dict)
            elif search_dict['storage_type'] == ResultType.output.value:
                return self.get_outputs(**search_dict)
        return None

    @result
    def get_experiments_data_frame(self, experiment_names=None, experiment_ids=None, inclusion_dicts=None, limit=10):
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

            experiment_ids.update([self.get_experiment(name).experiment_id
                                   for name in experiment_names if self.get_experiment(name) is not None])

        all_runs = []
        for e_id in experiment_ids:
            runs = self.list_run_infos(experiment_id=e_id)
            all_runs.extend(runs)
            if len(all_runs) > limit:
                all_runs = all_runs[:limit]
                break

        return self.get_data_frame([r.run_id for r in all_runs], inclusion_dicts=inclusion_dicts)

    @result
    def get_run_ids_by_search(self, search_dict) -> set:
        """
        Search for run ids by a search dict.
        The search dict has to contain a storage_type to denote which collection to search through.
        :param search_dict:
        :return:
        """
        # TODO are there more complex searches we don't know about possible?
        if "$or" in search_dict:
            dicts = search_dict["$or"]
            out = set()
            for d in dicts:
                out.union(self.get_run_ids_by_search(d))
            return out
        else:
            return {obj.run.uid for obj in self._get_by_dict(search_dict)}

    @result
    def get_data_frame(self, run_ids, inclusion_dicts=None):
        """
        Returns a pandas data frame containing results of the last runs of the experiment.
        @:param inclusion_dict: Search for run objects to include in the data frame for the found runs.
         Defaults to parameters, metrics and tags.
        :return:
        """
        if isinstance(run_ids, str):
            run_ids = {run_ids}
        elif isinstance(run_ids, list):
            run_ids = set(run_ids)

        if inclusion_dicts is None:
            inclusion_dicts = [{"storage_type": ResultType.parameter.value}, {"storage_type": ResultType.metric.value},
                               {"storage_type": ResultType.tag.value}]

        df = DataFrame()
        for run_id in run_ids:
            row = {}
            for search in inclusion_dicts:
                search["run.uid"] = run_id
                found = self._get_by_dict(search)
                row.update({m.storage_type.value + "_" + m.name: m for m in found})
            index = row.keys()
            data = row.values()
            run_series = Series(data=[v for v in data], index=index, name=run_id)
            df = df.append(run_series)
        return df

    # @result
    # def get_data_frame(self, experiment_names=None, experiment_ids=None, run_ids=None, search_dict=None):
    #     """
    #     Returns a pandas data frame containing results of the last runs of the experiment.
    #     The results contain all parameters and metrics as well as timestamps of the execution and notes about the runs.
    #     :return:
    #     """
    #     if search_dict is None:
    #         search_dict = {}
    #
    #     # Ids to set
    #     if experiment_ids is None:
    #         experiment_ids = set()
    #     elif isinstance(experiment_ids, str):
    #         experiment_ids = {experiment_ids}
    #     elif isinstance(experiment_ids, list):
    #         experiment_ids = set(experiment_ids)
    #
    #     # Names to ids
    #     if experiment_names is not None:
    #         if isinstance(experiment_names, str):
    #             experiment_names = {experiment_names}
    #
    #         experiment_ids.update([self.get_experiment(name).experiment_id
    #                                for name in experiment_names if self.get_experiment(name) is not None])
    #
    #     # Run ids
    #     if run_ids is not None:
    #         if isinstance(run_ids, str):
    #             run_ids = {run_ids}
    #         elif isinstance(run_ids, list):
    #             run_ids = set(run_ids)
    #
    #     df = DataFrame()
    #     # Add experiments
    #     for e_id in experiment_ids:
    #
    #         runs = self.list_run_infos(experiment_id=e_id)
    #         filtered_runs = [r for r in runs if run_ids is None or r.run_id in run_ids]
    #         for run_info in filtered_runs:
    #             run_id = run_info.run_id
    #
    #             curr_search_dict = search_dict.get(ResultType.metric, {})
    #             metrics = self.get_metrics(run_id=run_id, **curr_search_dict)
    #             metrics = {"m_" + m.name: m.data for m in metrics}
    #
    #             # We did not get any runs that satisfied the critieria
    #             if bool(curr_search_dict) and not bool(metrics):
    #                 continue
    #
    #             curr_search_dict = search_dict.get(ResultType.parameter, {})
    #             parameters = self.get_parameters(run_id=run_id, **curr_search_dict)
    #             parameters = {"p_" + p.name: p.data for p in parameters}
    #
    #             # We did not get any runs that satisfied the critieria
    #             if bool(curr_search_dict) and not bool(parameters):
    #                 continue
    #
    #             curr_search_dict = search_dict.get(ResultType.tag, {})
    #             tags = self.get_tags(run_id=run_id, **curr_search_dict)
    #             tags = {ResultType.tag: [(t.name, t.data) for t in tags]}
    #
    #             # We did not get any runs that satisfied the critieria
    #             if bool(curr_search_dict) and len(tags.get(ResultType.tag)) == 0:
    #                 continue
    #
    #             exp = {"experiment": e_id}
    #             run = {"start_time": run_info.start_time, "end_time": run_info.end_time}
    #             row = {**exp, **run, **metrics, **parameters, **tags}
    #             index = row.keys()
    #             data = row.values()
    #             run_series = Series(data=[v for v in data], index=index, name=run_id)
    #             df = df.append(run_series)
    #     return df


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
