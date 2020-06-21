import ast
import atexit
import importlib
import os
import pkgutil
from os.path import expanduser
from typing import List

import mlflow

from pypads import logger
from pypads.app.actuators import ActuatorPluginManager
from pypads.app.api import ApiPluginManager
from pypads.app.backend import MLFlowBackend
from pypads.app.decorators import DecoratorPluginManager
from pypads.app.misc.caches import PypadsCache
from pypads.app.validators import ValidatorPluginManager, validators
from pypads.bindings.events import FunctionRegistry
from pypads.bindings.hooks import HookRegistry
from pypads.importext.mappings import MappingRegistry, MappingCollection
from pypads.importext.pypads_import import extend_import_module, duck_punch_loader
from pypads.importext.wrapping.wrapping import WrapManager
from pypads.injections.analysis.call_tracker import CallTracker
from pypads.injections.setup.git import IGit
from pypads.injections.setup.hardware import ISystem, IRam, ICpu, IDisk, IPid, ISocketInfo, IMacAddress
from pypads.injections.setup.misc_setup import RunInfo, RunLogger

tracking_active = None

# --- Pypads App ---

"""
TODO keras:
Logs loss and any other metrics specified in the fit
    function, and optimizer data as parameters. Model checkpoints
    are logged as artifacts to a 'models' directory.
    EarlyStopping Integration with Keras Automatic Logging
    MLflow will detect if an ``EarlyStopping`` callback is used in a ``fit()``/``fit_generator()``
    call, and if the ``restore_best_weights`` parameter is set to be ``True``, then MLflow will
    log the metrics associated with the restored model as a final, extra step. The epoch of the
    restored model will also be logged as the metric ``restored_epoch``.
    This allows for easy comparison between the actual metrics of the restored model and
    the metrics of other models.
    If ``restore_best_weights`` is set to be ``False``,
    then MLflow will not log an additional step.
    Regardless of ``restore_best_weights``, MLflow will also log ``stopped_epoch``,
    which indicates the epoch at which training stopped due to early stopping.
    If training does not end due to early stopping, then ``stopped_epoch`` will be logged as ``0``.
    MLflow will also log the parameters of the EarlyStopping callback,
    excluding ``mode`` and ``verbose``.
"""

# Default config.
# Pypads mapping files shouldn't interact directly with the logging functions,
# but define events on which different logging functions can listen.
# This config defines such a listening structure.
# {"recursive": track functions recursively. Otherwise check the callstack to only track the top level function.}
DEFAULT_CONFIG = {
    "track_sub_processes": False,
    # Activate to track spawned subprocesses by extending the joblib. This is currently experimental.
    "recursion_identity": False,
    # Activate to ignore tracking on recursive calls of the same function with the same mapping
    "recursion_depth": -1,  # Limit the tracking of recursive calls
    "log_on_failure": True,  # Log the stdout / stderr output when the execution of the experiment failed
    "include_default_mappings": True  # Include the default mappings additionally to the passed mapping if a mapping
    # is passed
}

DEFAULT_SETUP_FNS = {RunInfo(), RunLogger(), IGit(_pypads_timeout=3), ISystem(), IRam(), ICpu(), IDisk(), IPid(),
                     ISocketInfo(), IMacAddress()}

# Tag name to save the config to in mlflow context.
CONFIG_NAME = "pypads.config"


#  pypads isn't allowed to hold a state anymore (Everything with state should be part of the caching system)
#  - We want to be able to rebuild PyPads from the cache alone if existing
#  to stop the need for pickeling pypads as a whole.

class PyPads:
    """
    PyPads app. Serves as the main entrypoint to PyPads. After constructing this app tracking is activated.
    """

    def __init__(self, uri=None, folder=None, mappings: List[MappingCollection] = None, hooks=None,
                 events=None, setup_fns=None, config=None, pre_initialized_cache: PypadsCache = None,
                 disable_plugins=None, autostart=None):
        # Set the singleton instance

        if disable_plugins is None:
            disable_plugins = []
        for name, plugin in discovered_plugins.items():
            if name not in disable_plugins:
                plugin.activate()

        from pypads.app.pypads import set_current_pads
        set_current_pads(self)

        # Init variable to filled later in this constructor
        self._atexit_fns = []

        # Init WrapManager
        self._wrap_manager = WrapManager(self)

        # Init API
        self._api = ApiPluginManager()

        # Init Decorators
        self._decorators = DecoratorPluginManager()

        # Init Actuators
        self._actuators = ActuatorPluginManager()

        # Init Validators
        self._validators = ValidatorPluginManager()

        # Init CallTracker
        self._call_tracker = CallTracker(self)

        # Init cache
        self._cache = pre_initialized_cache if pre_initialized_cache else PypadsCache()

        # Store folder into cache
        self._cache.add("folder", folder or os.path.join(expanduser("~"), ".pypads"))

        # Store uri into cache
        self._cache.add("uri", uri or os.environ.get('MLFLOW_PATH') or os.path.join(self.folder, ".mlruns"))

        self._backend = MLFlowBackend(self.uri, self)

        # Enable git tracking of the current repository
        from pypads.app.misc.managed_git import ManagedGitFactory
        self._managed_git_factory = ManagedGitFactory(self)

        # Store config into cache
        self.config = config or DEFAULT_CONFIG

        # Store config into cache
        self._cache.add("mappings", mappings)

        # Store hook registry into cache
        self._cache.add("hooks", hooks)

        # Store function registry into cache
        self._cache.add("events", events)

        # Init mapping registry
        self._mapping_registry = MappingRegistry.from_params(self, mappings)

        # Init hook registry
        self._hook_registry = HookRegistry.from_dict(self, hooks)

        # Init function registry
        self._function_registry = FunctionRegistry.from_dict(self, events)

        # Store config into cache
        self._cache.add("mappings", mappings)

        # Store hook registry into cache
        self._cache.add("hooks", hooks)

        # Store function registry into cache
        self._cache.add("events", events)

        # Initialize pre run functions before starting a run
        setup_fns = setup_fns or DEFAULT_SETUP_FNS
        for fn in setup_fns:
            self.api.register_setup(fn.__class__.__name__ + "_" + str(id(fn)), fn)

        # Activate tracking by punching the import lib
        if autostart:
            self.activate_tracking()

        # Add cleanup functions
        def cleanup():
            from pypads.app.pypads import get_current_pads
            pads: PyPads = get_current_pads()
            if pads.api.active_run():
                pads.api.end_run()

        self.add_atexit_fn(cleanup)

        if autostart:
            if isinstance(autostart, str):
                self.start_track(autostart)
            else:
                self.start_track()

    @staticmethod
    def available_loggers():
        """
        Return a list of available LoggingFunctions for mappings in the current installation of PyPads.
        :return: Logging function classes
        """
        from pypads.app.injections.base_logger import logging_functions
        return logging_functions()

    @staticmethod
    def available_setup_functions():
        """
        Return a list of available setup function in the current installation of PyPads.
        :return: Setup function classes
        """
        from pypads.app.injections.run_loggers import pre_run_functions
        return pre_run_functions()

    @staticmethod
    def available_teardown_functions():
        """
        Return a list of available setup function in the current installation of PyPads.
        :return: Teardown function classes
        """
        from pypads.app.injections.run_loggers import post_run_functions
        return post_run_functions()

    @staticmethod
    def available_anchors():
        """
        Return a list of available anchors in the current installation of PyPads. Anchors are names for hooks.
        :return: Anchors
        """
        from pypads.bindings.anchors import anchors
        return anchors

    @staticmethod
    def available_events():
        """
        Return a list of available events (event types) in the current installation of PyPads. Events are triggered by hooks and map to functions.
        :return: Event types
        """
        from pypads.bindings.event_types import event_types
        return event_types

    @staticmethod
    def available_validators():
        """
        Return a list of available validators in the current installation of PyPads.
        :return: Validator classes
        """
        return validators()

    @staticmethod
    def available_decorators():
        """
        Return a list of available decorators in the current installation of PyPads.
        :return: Decorator classes
        """
        from pypads.app.decorators import decorators
        return decorators()

    @staticmethod
    def available_actuators():
        """
        Return a list of available actuators in the current installation of PyPads.
        :return: Actuator classes
        """
        from pypads.app.actuators import actuators
        return actuators()

    @staticmethod
    def available_cmds():
        """
        Return a list of available api commands in the current installation of PyPads.
        :return: API commands classes
        """
        from pypads.app.api import api
        return api()

    @property
    def cache(self):
        """
        Return the cache of pypads. This holds generic cache data and run cache data.
        :return:
        """
        return self._cache

    @property
    def uri(self):
        """
        Return the tracking uri pypads uses for mlflow.
        :return:
        """
        return self._cache.get("uri")

    @property
    def folder(self):
        """
        Return the local folder pypads uses for its temporary storage, configuration etc.
        :return:
        """
        return self._cache.get("folder")

    @property
    def config(self):
        """
        Return the configuration of pypads.
        :return: Configuration dict
        """
        if self._cache.exists("config"):
            return self._cache.get("config")
        if self.api.active_run() is not None:
            tags = self.mlf.get_run(mlflow.active_run().info.run_id).data.tags
            if CONFIG_NAME not in tags:
                raise Exception("Config for pypads is not defined.")
            try:
                return ast.literal_eval(tags[CONFIG_NAME])
            except Exception as e:
                raise Exception("Config for pypads is malformed. " + str(e))
        else:
            return {}

    @config.setter
    def config(self, value: dict):
        """
        Set the configuration of pypads.
        :param value: Dict containing config key, values
        :return:
        """
        # Set the config as tag
        if self.api.active_run() is not None:
            mlflow.set_tag(CONFIG_NAME, value)
        else:
            # Set the config as soon as the run is started as tag
            def set_config(*args, **kwargs):
                mlflow.set_tag(CONFIG_NAME, value)

            self.api.register_setup_fn("config_persist", set_config, nested=False, intermediate=False)
        self._cache.add("config", value)

    @property
    def mapping_registry(self):
        """
        Access the mapping registry holding all references to mapping files etc.
        :return: Mapping registry
        """
        return self._mapping_registry

    @property
    def mappings(self):
        """
        Get the to the constructor passed mappings.
        :return: Additional mapping files.
        """
        return self._cache.get("mappings")

    @property
    def hook_registry(self):
        """
        Access the hook registry holding all mappings of anchors/hooks to events
        :return: Hook registry
        """
        return self._hook_registry

    @property
    def hooks(self):
        """
        Get the to the constructor passed hook / event mappings.
        :return: Hook configuration.
        """
        return self._cache.get("hooks")

    @property
    def function_registry(self):
        """
        Access the function registry holding all mappings of events to logging functions
        :return: Function registry
        """
        return self._function_registry

    @property
    def events(self):
        """
        Get the to the constructor passed event / logging function mappings.
        :return: Hook configuration.
        """
        return self._cache.get("events")

    @property
    def api(self):
        """
        Access the api of pypads.
        :return: PyPadsAPI
        """
        return self._api

    @property
    def decorators(self):
        """
        Access the decorators of pypads.
        :return: PyPadsDecorators
        """
        return self._decorators

    @property
    def validators(self):
        """
        Access the validators of pypads.
        :return: PyPadsValidators
        """
        return self._validators

    @property
    def actuators(self):
        """
        Access the actuators of pypads.
        :return: PyPadsActuators
        """
        return self._actuators

    @property
    def wrap_manager(self):
        """
        Return the wrap manager of PyPads. This is used to wrap modules, functions and classes.
        :return: WrapManager
        """
        return self._wrap_manager

    @property
    def call_tracker(self):
        """
        Return the call tracker of PyPads. This is used to keep track of the calls of hooked functions.
        :return: CallTracker
        """
        return self._call_tracker

    @property
    def backend(self):
        """
        Return the backend of PyPads. This is currently hardcoded to mlflow.
        :return: Backend
        """
        return self._backend

    @property
    def mlf(self):
        """
        Return a mlflow client to interact with stored data.
        :return: MlflowClient
        """
        return self._backend.mlf

    def add_atexit_fn(self, fn):
        """
        Add function to be executed before stopping your process. This function is also added to pypads and errors
        are caught to not impact the experiment itself. Deactivating pypads should be able to run some of the atExit fns
        declared for pypads.
        """

        def defensive_atexit():
            try:
                return fn()
            except (KeyboardInterrupt, Exception) as e:
                logger.error("Couldn't run atexit function " + fn.__name__ + " because of " + str(e))

        self._atexit_fns.append(defensive_atexit)
        atexit.register(defensive_atexit)

    def is_affected_module(self, name, affected_modules=None):
        """
        Check if a given module name is in the list of affected modules.
        You can pass a list of affected modules or take the one of the wrap_manager.
        :param name: Name of the module to check
        :param affected_modules: The list of affected modules (can be None and will be extracted automatically)
        :return:
        """
        if affected_modules is None:
            affected_modules = self.wrap_manager.module_wrapper.punched_module_names

        affected = set([module.split(".", 1)[0] for module in affected_modules])
        return any([name.startswith(module + ".") or name == module for module in affected]) or any(
            [name.startswith(module + ".") or name == module for module in
             affected_modules])

    def activate_tracking(self, reload_modules=False, reload_warnings=True, clear_imports=False, affected_modules=None):
        """
        Function to duck punch all objects defined in the mapping files. This should at best be called before importing
        any libraries.
        :param affected_modules: Affected modules of the mapping files.
        :param clear_imports: Clear imports after punching. CAREFUL THIS IS EXPERIMENTAL!
        :param reload_warnings: Show warnings of affected modules which were already imported before the importlib was extended.
        :param reload_modules: Force a reload of affected modules. CAREFUL THIS IS EXPERIMENTAL!
        :return:
        """
        if affected_modules is None:
            # Modules are affected if they are mapped by a library or are already punched
            affected_modules = self.wrap_manager.module_wrapper.punched_module_names | set(
                [l.name for l in self.mapping_registry.get_libraries()])

        global tracking_active
        if not tracking_active:
            from pypads.app.pypads import set_current_pads
            set_current_pads(self)

            # Add our loader to the meta_path
            extend_import_module()

            import sys
            import importlib
            loaded_modules = [(name, module) for name, module in sys.modules.items()]
            for name, module in loaded_modules:
                if self.is_affected_module(name, affected_modules):
                    if reload_warnings:
                        logger.warning(
                            name + " was imported before PyPads. To enable tracking import PyPads before or use "
                                   "reload_modules / clear_imports. Every already created instance is not tracked.")

                    if clear_imports:
                        del sys.modules[name]

                    if reload_modules:
                        try:
                            spec = importlib.util.find_spec(module.__name__)
                            duck_punch_loader(spec)
                            loader = spec.loader
                            module = loader.load_module(module.__name__)
                            loader.exec_module(module)
                            importlib.reload(module)
                        except Exception as e:
                            logger.debug("Couldn't reload module " + str(e))

            tracking_active = True
        else:
            raise Exception("Currently only one tracker can be activated at once.")
        return self

    def deactivate_tracking(self, run_atexits=False, reload_modules=True):
        """
        Deacticate the current tracking and cleanup.
        :param run_atexits: Run the registered atexit functions of pypads
        :param reload_modules: Force a reload of affected modules
        :return:
        """
        # run atexit fns if needed
        if run_atexits:
            for fn in self._atexit_fns:
                fn()

        # Remove atexit fns
        for fn in self._atexit_fns:
            atexit.unregister(fn)

        import sys
        import importlib
        loaded_modules = [(name, module) for name, module in sys.modules.items()]
        for name, module in loaded_modules:
            if self.is_affected_module(name):
                del sys.modules[name]

                if reload_modules:
                    # reload modules if they where affected
                    try:
                        spec = importlib.util.find_spec(module.__name__)
                        duck_punch_loader(spec)
                        loader = spec.loader
                        module = loader.load_module(module.__name__)
                        loader.exec_module(module)
                        importlib.reload(module)
                    except Exception as e:
                        logger.debug("Couldn't reload module " + str(e))

        global tracking_active
        tracking_active = False
        # noinspection PyTypeChecker
        from pypads.app.pypads import set_current_pads
        set_current_pads(None)

    def start_track(self, experiment_name="Default-PyPads", disable_run_init=False):
        """
        Start a new run to track.
        :param experiment_name: The name of the mlflow experiment
        :param disable_run_init: Flag to indicate if the run_init functions are to be run on an already existing run.
        :return:
        """
        if not tracking_active:
            self.activate_tracking()

        # check if there is already an active run
        run = mlflow.active_run()
        if run is None:
            # Create run if run doesn't already exist
            experiment_name = experiment_name
            experiment = mlflow.get_experiment_by_name(experiment_name)
            experiment_id = experiment.experiment_id if experiment else mlflow.create_experiment(experiment_name)
            run = self.api.start_run(experiment_id=experiment_id)
        else:
            # Run init functions if run already exists but tracking is starting for it now
            if not disable_run_init:
                self.api.run_setups()
        _experiment = self.backend.mlf.get_experiment_by_name(
            experiment_name) if experiment_name else self.backend.mlf.get_experiment(run.info.experiment_id)

        # override active run if used
        if experiment_name and run.info.experiment_id is not _experiment.experiment_id:
            logger.warning("Active run doesn't match given input name " + experiment_name + ". Recreating new run.")
            try:
                self.api.start_run(experiment_id=_experiment.experiment_id, nested=True)
            except Exception:
                mlflow.end_run()
                self.api.start_run(experiment_id=_experiment.experiment_id)
        return self


# --- Pypads Plugins ---
discovered_plugins = {
    name: importlib.import_module(name)
    for finder, name, ispkg
    in pkgutil.iter_modules()
    if name.startswith('pypads_')
}
