.. _base_class:

============
PyPads application class
============

This class represents the app. To start and activate the tracking of your modules, classes and functions, the app class has to be instantiated.

.. warning::
    It is recommended to initialize the tracking **before** importing the modules to be tracked. While extending the importlib and reloading the modules may work sometimes doing so may result in unforeseen issues.

.. autoclass::
    pypads.app.base.PyPads

.. _default_setting:


Default settings
================

The app includes default values for configuration, hook/event mappings, event/function mappings etc.


Default Anchors
----------------

Anchors are names for repeating types of hooks. Fit functions for example are existing on multiple libraries.

.. code-block:: python

    DEFAULT_ANCHORS = [Anchor("pypads_init", "Used if a tracked concept is initialized."),
                       Anchor("pypads_fit", "Used if an model is fitted to data."),
                       Anchor("pypads_predict", "Used if an model predicts something."),
                       Anchor("pypads_metric", "Used if an metric is compiled."),
                       Anchor("pypads_log", "Used to only log a call.")]



Default Event Types
----------------

Event types represent strategies to react to an anchor / hook.

.. code-block:: python

    DEFAULT_EVENT_TYPES = [EventType("parameters", "Track the parameters for given model."),
                           EventType("output", "Track the output of the function."),
                           EventType("input", "Track the input of the function."),
                           EventType("hardware", "Track current hardware load on function execution."),
                           EventType("metric", "Track a metric."),
                           EventType("autolog", "Activate mlflow autologging."),
                           EventType("pipeline", "Track a pipeline step."),
                           EventType("log", "Log the call to console."),
                           EventType("init", "Log the tracked class init to console.")]


Default Config
----------------

The configuration for PyPads

.. code-block:: python

    DEFAULT_CONFIG = {
        "track_sub_processes": False,  # Activate to track spawned subprocesses by extending the joblib
        "recursion_identity": False, # Activate to ignore tracking on recursive calls of the same function with the same mapping
        "recursion_depth": -1,  # Limit the tracking of recursive calls
        "log_on_failure": True,  # Log the stdout / stderr output when the execution of the experiment failed
        "include_default_mappings": True  # Include the default mappings additionally to the passed mapping if a mapping is passed
    }


Default Hook Mapping
----------------

The hook mapping, maps hooks (anchors) to the events (event types).

.. code-block:: python

    DEFAULT_HOOK_MAPPING = {
        "init": {"on": ["pypads_init"]},
        "parameters": {"on": ["pypads_fit"]},
        "hardware": {"on": ["pypads_fit"]},
        "output": {"on": ["pypads_fit", "pypads_predict"]},
        "input": {"on": ["pypads_fit"], "with": {"_pypads_write_format": FileFormats.text.name}},
        "metric": {"on": ["pypads_metric"]},
        "pipeline": {"on": ["pypads_fit", "pypads_predict", "pypads_transform", "pypads_metric"]},
        "log": {"on": ["pypads_log"]}
    }


Default Event Mapping
----------------

Defines which logging functions should be run for events.

.. code-block:: python

    DEFAULT_LOGGING_FNS = {
        "parameters": Parameters(),
        "output": Output(_pypads_write_format=FileFormats.text.name),
        "input": Input(_pypads_write_format=FileFormats.text.name),
        "hardware": [Cpu(), Ram(), Disk()],
        "metric": Metric(),
        "autolog": MlflowAutologger(),
        "pipeline": PipelineTracker(_pypads_pipeline_type="normal", _pypads_pipeline_args=False),
        "log": Log(),
        "init": LogInit()
    }
