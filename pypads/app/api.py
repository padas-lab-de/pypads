import os
from abc import ABCMeta
from contextlib import contextmanager
from functools import wraps
from typing import List, Iterable, Union

import mlflow

from pypads import logger
from pypads.app.env import LoggerEnv
from pypads.app.injections.base_logger import dummy_logger
from pypads.app.injections.run_loggers import RunSetup, RunTeardown, SimpleRunFunction
from pypads.app.injections.tracked_object import LoggerOutput, ParameterTO, TagTO, ArtifactTO, MetricTO
from pypads.app.misc.caches import Cache
from pypads.app.misc.extensions import ExtendableMixin, Plugin
from pypads.app.misc.mixins import FunctionHolderMixin
from pypads.bindings.anchors import get_anchor, Anchor
from pypads.importext.mappings import Mapping, MatchedMapping, make_run_time_mapping_collection
from pypads.importext.package_path import PackagePathMatcher, PackagePath
from pypads.utils.logging_util import get_temp_folder, FileFormats, read_artifact, find_file_format
from pypads.utils.util import get_experiment_id, get_run_id

api_plugins = set()
cmds = set()


class Cmd(FunctionHolderMixin, metaclass=ABCMeta):

    def __init__(self, *args, fn, **kwargs):
        super().__init__(*args, fn=fn, **kwargs)
        cmds.add(self)

    def __call__(self, *args, **kwargs):
        return self.__real_call__(*args, **kwargs)


class IApi(Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(type=Cmd, *args, **kwargs)
        api_plugins.add(self)

    def _get_meta(self):
        """ Method returning information about where the actuator was defined."""
        return self.__module__

    def _get_methods(self):
        return [method_name for method_name in dir(self) if callable(getattr(object, method_name))]


def cmd(f):
    """
    Decorator used to convert a function to a tracked actuator.
    :param f:
    :return:
    """

    api_cmd = Cmd(fn=f)

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        # self is an instance of the class
        return api_cmd(self, *args, **kwargs)

    return wrapper


class PyPadsApi(IApi):
    """
    Default api functions of pypads
    """

    def __init__(self):
        super().__init__()

    @property
    def pypads(self):
        from pypads.app.pypads import get_current_pads
        return get_current_pads()

    # noinspection PyMethodMayBeStatic
    @cmd
    def track(self, fn, ctx=None, anchors: List = None, mapping: Mapping = None, additional_data=None):
        """
        Method to inject logging capabilities into a function
        :param additional_data: Additional meta data to be provided to the tracking. This should be used to map to rdf.
        :param fn: Function to extend
        :param ctx: Ctx which defined the function
        :param anchors: Anchors to trigger on function call
        :param mapping: Mapping defining this extension
        :return: The extended function
        """
        if additional_data is None:
            additional_data = {}

        # Warn if ctx doesn't defined the function we want to track
        if ctx is not None and not hasattr(ctx, fn.__name__):
            logger.warning("Given context " + str(ctx) + " doesn't define " + str(fn.__name__))
            ctx = None

        # If we don't have a valid ctx the fn is unbound, otherwise we can extract the ctx path
        if ctx is not None:
            if hasattr(ctx, '__module__') and ctx.__module__ is not str.__class__.__module__:
                ctx_path = ctx.__module__.__name__
            else:
                ctx_path = ctx.__name__
        else:
            ctx_path = "<unbound>"

        if anchors is None:
            anchors = [get_anchor("pypads_log")]
        elif not isinstance(anchors, Iterable):
            anchors = [anchors]

        _anchors = set()
        for a in anchors:
            if isinstance(a, str):
                anchor = get_anchor(a)
                if anchor is None:
                    anchor = Anchor(a, "No description available")
                _anchors.add(anchor)
            elif isinstance(a, Anchor):
                _anchors.add(a)

        # If no mapping was given a default mapping has to be created
        if mapping is None:
            logger.warning("Tracking a function without a mapping definition. A default mapping will be generated.")
            if '__file__' in fn.__globals__:
                lib = fn.__globals__['__file__']
            else:
                lib = fn.__module__

            # For all events we want to hook to
            mapping = Mapping(PackagePathMatcher(ctx_path + "." + fn.__name__), make_run_time_mapping_collection(lib),
                              _anchors,
                              {**additional_data, **{"mapped_by": "http://www.padre-lab.eu/onto/PyPadsApi"}})

        # Wrap the function of given context and return it
        return self.pypads.wrap_manager.wrap(fn, ctx=ctx, matched_mappings={MatchedMapping(mapping, PackagePath(
            ctx_path + "." + fn.__name__))})

    @cmd
    def start_run(self, run_id=None, experiment_id=None, run_name=None, nested=False, _pypads_env=None, setups=True):
        """
        Method to start a new mlflow run. And run its setup functions.
        Every run is supposed to be an own execution. This may make sense if a single file defines multiple executions
        you want to track. (Entry to hyperparameter searches?)
        :param setups: Flag to indicate setup functions should be run
        :param run_id: The id the run should get. This will be chosen automatically if None.
        :param experiment_id: The id the parent experiment has.
        :param run_name: A name for the run. This will also be chosen automatically if None.
        :param nested: If the run should be a nested run. (Run spawned in context of another run)
        :param _pypads_env: Pass the logging env if one is set.
        :return: The newly spawned run
        """
        out = mlflow.start_run(run_id=run_id, experiment_id=experiment_id, run_name=run_name, nested=nested)
        if setups:
            self.run_setups(
                _pypads_env=_pypads_env or LoggerEnv(parameter=dict(), experiment_id=experiment_id, run_id=run_id,
                                                     data={"category": "SetupFn"}))
        return out

    # ---- logging ----
    def get_programmatic_output(self):
        if not self.pypads.cache.run_exists("programmatic_output"):
            self.pypads.cache.run_add("programmatic_output",
                                      LoggerOutput(_pypads_env=self.create_dummy_env(), producer=dummy_logger))

        return self.pypads.cache.run_get("programmatic_output")

    @staticmethod
    def create_dummy_env(data=None) -> LoggerEnv:
        """
        Create a dummy environment to be used for programmatically called logging instead of hooks
        :param data:
        :return:
        """
        if data is None:
            data = {}
        return LoggerEnv(parameter=dict(), experiment_id=get_experiment_id(), run_id=get_run_id(),
                         data={**data, **{"programmatic": True}})

    @cmd
    def log_artifact(self, local_path, description="", additional_data=None, artifact_path=None, holder=None):
        """
        Function to log an artifact on local disk. This artifact is transferred into the context of mlflow.
        The context might be a local repository, sftp etc.
        :param holder: Output model to which to add the artifact
        :param description: Description of the artifact.
        :param artifact_path: Path where to store the artifact
        :param local_path: Path of the artifact to log
        :param additional_data: Additional meta information you want to store about the artifact. This is an extension by pypads creating a
        json containing some meta information.
        :return:
        """
        if holder is None:
            holder = self.get_programmatic_output()
        ato = ArtifactTO(value=artifact_path, description=description, file_format=find_file_format(local_path),
                         additional_data=additional_data, parent=holder)
        out = self.pypads.backend.log_artifact(ato, local_path)
        holder.add_result(ato)
        return out

    @cmd
    def log_mem_artifact(self, path, obj, write_format=FileFormats.text, description="", additional_data=None,
                         holder=None):
        """
        See log_artifact. This logs directly from memory by storing the memory to a temporary file.
        :param holder: Output model to which to add the artifact
        :param description: Description of the artifact.
        :param path: path of the new file to create.
        :param obj: Object you want to store
        :param write_format: Format to write to. FileFormats currently include text and binary.
        :param additional_data: Meta information you want to store about the artifact.
        This is an extension by pypads creating a
        json containing some meta information.
        :return:
        """
        if holder is None:
            holder = self.get_programmatic_output()
        return ArtifactTO(data=path, content=obj, description=description, file_format=write_format,
                          additional_data=additional_data, parent=holder).store()

    @cmd
    def log_metric(self, key, value, description="", step=0, additional_data: dict = None, holder=None):
        """
        Log a metric to mlflow.
        :param holder: Output model to which to add the artifact
        :param description: Description of the metric.
        :param key: Metric key
        :param value: Metric value
        :param step: A step for metrics which can change while executing
        :param additional_data: Meta information you want to store about the metric. This is an extension by pypads creating a
        json containing some meta information.
        :return:
        """
        if holder is None:
            holder = self.get_programmatic_output()
        return MetricTO(name=key, step=step, data=value, description=description, additional_data=additional_data,
                        parent=holder).store()

    @cmd
    def log_param(self, key, value, value_format=None, description="", additional_data: dict = None, holder=None):
        """
        Log a parameter of the execution.
        :param holder: Output model to which to add the artifact
        :param value_format: Type of the parameter
        :param description: Description of the parameter.
        :param key: Parameter key
        :param value: Parameter value
        :param additional_data: Meta information you want to store about the parameter. This is an extension by pypads
        creating a json containing some meta information.
        :return:
        """
        if holder is None:
            holder = self.get_programmatic_output()
        return ParameterTO(name=key, value_format=value_format or str(type(value)),
                           description=description, additional_data=additional_data,
                           data=value, parent=holder).store()

    @cmd
    def set_tag(self, key, value, value_format="string", description="", additional_data: dict = None,
                holder=None):
        """
        Set a tag for your current run.
        :param holder: Output model to which to add the artifact
        :param additional_data: Meta information you want to store about the parameter. This is an extension by
        pypads creating a json containing some meta information.
        :param value_format: Format of the value held in tag
        :param description: Description what this tag indicates
        :param key: Tag key
        :param value: Tag value
        :return:
        """
        if holder is None:
            holder = self.get_programmatic_output()
        return self.pypads.backend.log(
            TagTO(name=key, value_format=value_format or str(type(value)),
                  description=description, additional_data=additional_data,
                  data=value,
                  parent=holder))

    @cmd
    def artifact(self, name):
        return read_artifact(name)

    # !--- logging ----

    # ---- run management ----
    @contextmanager
    @cmd
    def intermediate_run(self, setups=True, nested=True, clear_cache=True, **kwargs):
        """
        Spawn an intermediate nested run.
        This run closes automatically after the "with" block and restarts the parent run.
        :param setups: Flag to indicate setup functions should be run. TODO teardowns?
        :param nested: Start run as nested run.
        :param kwargs: Other kwargs to pass to start_run()
        :return:
        """
        enclosing_run = mlflow.active_run()
        try:
            run = self.pypads.api.start_run(**kwargs, setups=setups, nested=nested)
            self.pypads.cache.run_add("enclosing_run", enclosing_run)
            yield run
        finally:
            if not mlflow.active_run() is enclosing_run:
                run_id = mlflow.active_run().info.run_id
                self.pypads.api.end_run()
                if clear_cache:
                    self.pypads.cache.run_clear(run_id=run_id)
                    self.pypads.cache.run_delete(run_id=run_id)
            else:
                mlflow.start_run(run_id=enclosing_run.info.run_id)

    def _get_setup_cache(self):
        """
        Get registered pre_run functions.
        :return:
        """
        if not self.pypads.cache.exists("pre_run_fns"):
            pre_run_fn_cache = Cache()
            self.pypads.cache.add("pre_run_fns", pre_run_fn_cache)
        return self.pypads.cache.get("pre_run_fns")

    @cmd
    def register_setup(self, name, pre_fn: Union[RunSetup, SimpleRunFunction], silent_duplicate=True):
        """
        Register a new pre_run function.
        :param name: Name of the registration
        :param pre_fn: Function to register
        :param silent_duplicate: Ignore log output if post_run was already registered.
        This makes sense if a logger running multiple times wants to register a single setup function.
        :return:
        """
        cache = self._get_setup_cache()
        if cache.exists(name):
            if not silent_duplicate:
                logger.debug("Pre run fn with name '" + name + "' already exists. Skipped.")
        else:
            cache.add(name, pre_fn)

    @cmd
    def register_setup_fn(self, name, description, fn, error_message=None, nested=True, intermediate=True, order=0,
                          silent_duplicate=True):
        """
        Register a new setup logger by building it from given parameters.
        :param error_message: Error message to log on failure.
        :param description: A description of the setup function.
        :param name: Name of the registration
        :param fn: Function to register
        :param nested: Parameter if this function should be called on nested runs.
        :param intermediate: Parameter if this function should be called on a intermediate run.
        An intermediate run is a nested run managed specifically by pypads.
        :param order: Value defining the execution order for pre run function.
        The lower the value the sooner a function gets executed.
        :param silent_duplicate: Ignore log output if post_run was already registered.
        :return:
        """

        class TmpRunSetupFunction(RunSetup):
            pass

        TmpRunSetupFunction.__doc__ = description

        self.register_setup(name,
                            TmpRunSetupFunction(fn=fn, message=error_message, nested=nested, intermediate=intermediate,
                                                order=order),
                            silent_duplicate=silent_duplicate)

    @cmd
    def register_setup_utility(self, name, fn, error_message=None, order=0, silent_duplicate=True):
        """
        Register a new utility function for setup. This is not a Logger.
        :param error_message: Error message to log on failure.
        :param name: Name of the registration
        :param fn: Function to register
        An intermediate run is a nested run managed specifically by pypads.
        :param order: Value defining the execution order for pre run function.
        The lower the value the sooner a function gets executed.
        :param silent_duplicate: Ignore log output if post_run was already registered.
        :return:
        """
        """
        Register a new cleanup function to do simple cleanup tasks after a run. This is not considered an own logger.
        """
        self.register_setup(name,
                            pre_fn=SimpleRunFunction(fn=fn, error_message=error_message, order=order),
                            silent_duplicate=silent_duplicate)

    @cmd
    def run_setups(self, _pypads_env=None):
        cache = self._get_setup_cache()
        fns = []
        for k, v in cache.items():
            fns.append(v)
        fns.sort(key=lambda f: f.order)
        for fn in fns:
            if callable(fn):
                fn(self, _pypads_env=_pypads_env)

    def _get_teardown_cache(self):
        """
        Get the teardown function registry from cache
        :return:
        """
        # General post run cache
        if not self.pypads.api.active_run():
            if not self.pypads.cache.exists("post_run_fns"):
                post_run_fn_cache = Cache()
                self.pypads.cache.add("post_run_fns", post_run_fn_cache)
            return self.pypads.cache.get("post_run_fns")

        # Post run cache for especially this run
        if not self.pypads.cache.run_exists("post_run_fns"):
            post_run_fn_cache = Cache()
            self.pypads.cache.run_add("post_run_fns", post_run_fn_cache)
        return self.pypads.cache.run_get("post_run_fns")

    @cmd
    def register_teardown(self, name, post_fn: Union[RunTeardown, SimpleRunFunction], silent_duplicate=True):
        """
        Register a new post run function.
        :param name: Name of the registration
        :param post_fn: Function to register
        :param silent_duplicate: Ignore log output if post_run was already registered.
        This makes sense if a logger running multiple times wants to register a single cleanup function.
        :return:
        """
        cache = self._get_teardown_cache()
        if cache.exists(name):
            if not silent_duplicate:
                logger.debug("Post run fn with name '" + name + "' already exists. Skipped.")
        else:
            cache.add(name, post_fn)

    @cmd
    def register_teardown_fn(self, name, fn, description="", error_message=None, nested=True, intermediate=True,
                             order=0,
                             silent_duplicate=True):
        """
        Register a new post_run_function by building it from given parameters. This is considered an own logger.
        :param description: Description for the run-teardown function.
        :param name: Name of the registration
        :param fn: Function to register
        :param error_message: Error message on failure.
        :param nested: Parameter if this function should be called on nested runs.
        :param intermediate: Parameter if this function should be called on a intermediate run.
        An intermediate run is a nested run managed specifically by pypads.
        :param order: Value defining the execution order for post run function.
        The lower the value the sooner a function gets executed.
        :param silent_duplicate: Ignore log output if post_run was already registered.
        :return:
        """

        class TmpRunTeardownFunction(RunTeardown):
            pass

        TmpRunTeardownFunction.__doc__ = description
        self.register_teardown(name,
                               post_fn=TmpRunTeardownFunction(fn=fn, error_message=error_message, nested=nested,
                                                              intermediate=intermediate, order=order),
                               silent_duplicate=silent_duplicate)

    @cmd
    def register_teardown_utility(self, name, fn, error_message=None,
                                  order=0, silent_duplicate=True):
        """
        Register a new cleanup function to do simple cleanup tasks after a run. This is not considered an own logger.
        """
        self.register_teardown(name,
                               post_fn=SimpleRunFunction(fn=fn, error_message=error_message, order=order),
                               silent_duplicate=silent_duplicate)

    @cmd
    def active_run(self):
        """
        Get the currently active run
        :return: Active run
        """
        return mlflow.active_run()

    @cmd
    def is_intermediate_run(self):
        """
        Check if the current run is an intermediate run.
        :return:
        """
        enclosing_run = self.pypads.cache.run_get("enclosing_run")
        return enclosing_run is not None

    @cmd
    def end_run(self):
        """
        End the current run and run its tearDown functions.
        :return:
        """
        run = self.active_run()

        # consolidated_dict = self.pypads.cache.get('consolidated_dict', None)
        # if consolidated_dict is not None:
        #     # Dump data to disk
        #     self.log_mem_artifact("consolidated_log", consolidated_dict, write_format=FileFormats.json)

        chached_fns = self._get_teardown_cache()
        fn_list = [v for i, v in chached_fns.items()]
        fn_list.sort(key=lambda t: t.order)
        for fn in fn_list:
            try:
                fn(self.pypads, _pypads_env=LoggerEnv(parameter=dict(), experiment_id=run.info.experiment_id,
                                                      run_id=run.info.run_id),
                   data={"category": "TearDownFn"})
            except (KeyboardInterrupt, Exception) as e:
                logger.warning("Failed running post run function " + fn.__name__ + " because of exception: " + str(e))

        mlflow.end_run()

        # --- Clean tmp files in disk cache after run ---
        folder = get_temp_folder(run)
        if os.path.exists(folder):
            import shutil
            shutil.rmtree(folder)
        # !-- Clean tmp files in disk cache after run ---

    # !--- run management ---

    @cmd
    def help(self):
        help_text = ""
        for command in api():
            help_text.join(command.__str__() + ": " + command.__doc__ + "\n\n")
        return help_text


class ApiPluginManager(ExtendableMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(plugin_list=api_plugins)


pypads_api = PyPadsApi()


def api():
    """
    Returns classes of
    :return:
    """
    command_list = list(cmds)
    command_list.sort(key=lambda a: str(a))
    return command_list
