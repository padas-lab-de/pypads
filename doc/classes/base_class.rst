.. _base_class:

============
PyPads Class
============

To start and activate the tracking of your modules, classes and functions, An instantiation of the base class has to be done.
.. note::
It is recommended to initialize the tracking **before** importing the modules to be tracked.

.. autoclass:: pypads.base.PyPads
    :members:
    :undoc-members:

.. _default_setting:

Default settings
================

The default configuration of events/hooks::

    DEFAULT_CONFIG = {"events": {
    "init": {"on": ["pypads_init"]},
    "parameters": {"on": ["pypads_fit"]},
    "hardware": {"on": ["pypads_fit"]},
    "output": {"on": ["pypads_fit", "pypads_predict"]},
    "input": {"on": ["pypads_fit"], "with": {"_pypads_write_format": WriteFormats.text.name}},
    "metric": {"on": ["pypads_metric"]},
    "pipeline": {"on": ["pypads_fit", "pypads_predict", "pypads_transform", "pypads_metric"]},
    "log": {"on": ["pypads_log"]}
    },
        "recursion_identity": False,
        "recursion_depth": -1,
        "log_on_failure": True}

The default mapping of events/loggers::

    DEFAULT_LOGGING_FNS = {
    "parameters": Parameters(),
    "output": Output(_pypads_write_format=WriteFormats.text.name),
    "input": Input(_pypads_write_format=WriteFormats.text.name),
    "hardware": {Cpu(), Ram(), Disk()},
    "metric": Metric(),
    "autolog": MlflowAutologger(),
    "pipeline": PipelineTracker(_pypads_pipeline_type="normal", _pypads_pipeline_args=False),
    "log": Log(),
    "init": LogInit()

