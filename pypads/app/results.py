from abc import ABCMeta
from functools import wraps
from typing import Union

from mlflow.entities import ViewType

from pypads.app.misc.extensions import ExtendableMixin, Plugin
from pypads.app.misc.mixins import FunctionHolderMixin
from pypads.model.logger_output import MetricMetaModel
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
    def list_run_infos(self, experiment_name, run_view_type: ViewType = ViewType.ALL):
        experiment = self.pypads.backend.get_experiment_by_name(experiment_name)
        return self.pypads.backend.list_run_infos(experiment_name=experiment.name, run_view_type=run_view_type)

    @result
    def get_metrics(self, experiment_name=None, run_id=None, **kwargs):
        return self.list(ResultType.metric, experiment_name=experiment_name, run_id=run_id,
                         search_dict=MetricMetaModel.construct(**kwargs).dict())

    @result
    def list(self, storage_type: Union[str, ResultType], experiment_name=None, experiment_id=None, run_id=None,
             search_dict=None):
        return self.pypads.backend.list(storage_type=storage_type, experiment_name=experiment_name,
                                        experiment_id=experiment_id, run_id=run_id, search_dict=search_dict)

    # @result
    # def get_metrics(self, experiment_name=None, run_id=None, name: str = None, view_type=ViewType.ALL, history=False):
    #     if run_id is None:
    #         # Get all experiments
    #         if experiment_name is None:
    #             experiments = self.pypads.backend.list_experiments(view_type=view_type)
    #             for experiment in experiments:
    #                 if not Repository.is_repository(experiment):
    #                     for metric in self.get_metrics(experiment_name=experiment.name, name=name, view_type=view_type, history=history):
    #                         yield metric
    #
    #         # Get all runs
    #         run_infos = self.pypads.backend.list_run_infos(experiment_name=experiment_name, run_view_type=view_type)
    #         for run_info in run_infos:
    #             for metric in self.get_metrics(run_id=run_info.run_id, name=name, view_type=view_type,
    #                                            history=history):
    #                 yield metric
    #     if not name:
    #         run = self.pypads.results.get_run(run_id)
    #         self.pypads.backend.get(run_id, )
    #     run = self.pypads.results.get_run(run_id)
    #     if name in run.data.metrics:
    #         return [MetricInfo(meta=self.pypads.backend.get_metric_meta(run_id=run.info.run_id, relative_path=name),
    #                            content=run.data.metrics[
    #                                name] if not history else self.pypads.backend.get_metric_history(
    #                                run.info.run_id, name))]
    #     return []

    # @result
    # def get_parameters(self, experiment_name=None, run_id=None, name: str = None, view_type=ViewType.ALL):
    #     if run_id is None:
    #         # Get all experiments
    #         if experiment_name is None:
    #             experiments = self.pypads.backend.list_experiments(view_type=view_type)
    #             return [parameter for experiment in experiments if
    #                     not Repository.is_repository(experiment) for parameter in
    #                     self.get_parameters(experiment_name=experiment.name, name=name)]
    #
    #         # Get all runs
    #         run_infos = self.pypads.backend.list_run_infos(experiment_name=experiment_name, run_view_type=view_type)
    #         return [parameter for run_info in run_infos for parameter in
    #                 self.get_parameters(run_id=run_info.run_id, name=name)]
    #     if not name:
    #         run = self.pypads.results.get_run(run_id)
    #         return [
    #             ParameterInfo(meta=self.pypads.backend.get_parameter_meta(run_id=run.info.run_id, relative_path=name),
    #                           content=run.data.params[name]) for name in run.data.params.keys()]
    #     run = self.pypads.results.get_run(run_id)
    #
    #     if name in run.data.params:
    #         return [
    #             ParameterInfo(meta=self.pypads.backend.get_parameter_meta(run_id=run.info.run_id, relative_path=name),
    #                           content=run.data.params[name])]
    #     return []
    #
    # @result
    # def get_tags(self, experiment_name=None, run_id=None, name: str = None, view_type=ViewType.ALL):
    #     if run_id is None:
    #         # Get all experiments
    #         if experiment_name is None:
    #             experiments = self.pypads.backend.list_experiments(view_type=view_type)
    #             return [tag for experiment in experiments if
    #                     not Repository.is_repository(experiment) for tag in
    #                     self.get_tags(experiment_name=experiment.name, name=name)]
    #
    #         # Get all runs
    #         run_infos = self.pypads.backend.list_run_infos(experiment_name=experiment_name, run_view_type=view_type)
    #         return [tag for run_info in run_infos for tag in
    #                 self.get_tags(run_id=run_info.run_id, name=name)]
    #     if not name:
    #         run = self.pypads.results.get_run(run_id)
    #         tags = []
    #         for name in iter(run.data.tags.keys()):
    #             tag_meta = None
    #             try:
    #                 tag_meta = self.pypads.backend.get_tag_meta(run_id=run.info.run_id, relative_path=name)
    #             except Exception:
    #                 pass
    #             if tag_meta:
    #                 tags.append(
    #                     TagInfo(meta=tag_meta,
    #                             content=run.data.tags[name]))
    #         return tags
    #
    #     run = self.pypads.results.get_run(run_id)
    #     if name in run.data.tags:
    #         return [TagInfo(meta=self.pypads.backend.get_tag_meta(run_id=run.info.run_id, relative_path=name),
    #                         content=run.data.tags[name])]
    #     return []
    #
    # @result
    # def get_artifacts(self, experiment_name=None, run_id=None, path: str = None, view_type=ViewType.ALL):
    #     if run_id is None:
    #         # Get all experiments
    #         if experiment_name is None:
    #             experiments = self.pypads.backend.list_experiments(view_type=view_type)
    #             return [artifact for experiment in experiments if
    #                     not Repository.is_repository(experiment) for artifact in
    #                     self.get_artifacts(experiment_name=experiment.name, path=path)]
    #
    #         # Get all runs
    #         run_infos = self.pypads.backend.list_run_infos(experiment_name=experiment_name, run_view_type=view_type)
    #         return [artifact for run_info in run_infos for artifact in
    #                 self.get_artifacts(run_id=run_info.run_id, path=path)]
    #     else:
    #
    #         # Check for searching all artifacts
    #         if path is not None:
    #             wildcard = path.endswith("*")
    #             if wildcard:
    #                 path = path[:-2]
    #
    #             if path == "":
    #                 path = None
    #
    #             current = self.pypads.backend.list_non_meta_files(run_id=run_id, path=path)
    #
    #             artifacts = []
    #             for c in current:
    #                 if c.is_dir:
    #                     if wildcard:
    #                         artifacts.extend(self.get_artifacts(run_id=run_id, path=os.path.join(c.path, "*")))
    #                 else:
    #                     artifacts.append(ArtifactInfo(file_size=c.file_size,
    #                                                   meta=self.pypads.backend.get_artifact_meta(run_id=run_id,
    #                                                                                              relative_path=c.path)))
    #             return artifacts
    #
    #         # Get a certain run
    #         return self.pypads.backend.list_artifacts(run_id=run_id, path=path)

    # @result
    # def search_artifacts_json_path(self, experiment_name=None, run_id=None, path: str = None, view_type=ViewType.ALL,
    #                                search=""):
    #     """
    #     Searches in meta information of the artifacts.
    #     :return:
    #     """
    #     return [a for a in [r.dict() for r in self.get_artifacts(experiment_name, run_id, path, view_type)] if
    #             len(jsonpath_rw_ext.match(search, a.meta)) > 0]
    #
    # @result
    # def get_logger_calls(self, experiment_name=None, run_id=None, path: str = None, view_type=ViewType.ALL):
    #     return self.search_artifacts_json_path(experiment_name=experiment_name, run_id=run_id, path=path,
    #                                            view_type=view_type, search="$[?(@.meta.type == 'Call')]")
    #
    # @result
    # def get_tracked_objects(self, experiment_name=None, run_id=None, path: str = None, view_type=ViewType.ALL):
    #     return self.search_artifacts_json_path(experiment_name=experiment_name, run_id=run_id, path=path,
    #                                            view_type=view_type, search="$[?(@.meta.type == 'TrackedObject')]")
    #
    # @result
    # def get_outputs(self, experiment_name=None, run_id=None, path: str = None, view_type=ViewType.ALL):
    #     return self.search_artifacts_json_path(experiment_name=experiment_name, run_id=run_id, path=path,
    #                                            view_type=view_type, search="$[?(@.meta.type == 'Outputs')]")


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
