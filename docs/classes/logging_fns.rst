.. _loggingfns:

=================
Logging functions
=================

LoggingFunction base class
==========================
To develop custom loggers, we need to write a class that inherits from the base class **LoggingFunction**. Then, those custom loggers can be
mapped to events of the user choice in the parameter **mapping** of the :ref:`PyPads class <base_class>`.

.. autoclass:: pypads.functions.loggers.base_logger.LoggingFunction
    :special-members: __pre__, __post__, __call_wrapped__
    :private-members: _needed_packages

Pre and Post run loggers
========================

Another type of logging functions supported by Pypads is the pre/post run loggers which are executed before and after the run execution
respectively.

* Pre Run loggers

.. autoclass:: pypads.functions.pre_run.pre_run.PreRunFunction
    :private-members: _call

* Post Run loggers

.. autoclass:: pypads.functions.post_run.post_run.PostRunFunction
    :private-members: _call


Mlflow autolog (experimental)
=============================

Pypads also support mlflow autologging functionalities. More on that can be found at `MLflow <https://mlflow.org/docs/latest/tracking.html#automatic-logging>`_.

.. autoclass:: pypads.functions.loggers.mlflow.mlflow_autolog.MlflowAutologger
    :special-members: __call_wrapped__
