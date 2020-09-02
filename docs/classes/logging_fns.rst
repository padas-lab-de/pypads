.. _loggingfns:

=================
Logging functions
=================

LoggingFunction base class
==========================
To develop custom loggers, we need to write a class that inherits from the base class **LoggingFunction**. Then, those custom loggers can be
mapped to events of the user choice in the parameter **mapping** of the :ref:`PyPads class <base_class>`.

.. autoclass:: pypads.app.injections.injection.InjectionLogger
    :special-members: __pre__, __post__, __call_wrapped__
    :private-members: _needed_packages

Setup and Teardown run loggers
==============================

Another type of logging functions supported by Pypads is the Setup/Teardown run loggers which are executed before and after the run execution
respectively.

* Run Setup loggers

.. autoclass:: pypads.app.injections.run_loggers.RunSetup
    :private-members: _call

* Post Run loggers

.. autoclass:: pypads.app.injections.run_loggers.RunTeardown
    :private-members: _call


Mlflow autolog (experimental)
=============================

Pypads also support mlflow autologging functionalities. More on that can be found at `MLflow <https://mlflow.org/docs/latest/tracking.html#automatic-logging>`_.

.. autoclass:: pypads.injections.loggers.mlflow.mlflow_autolog.MlflowAutologger
    :special-members: __call_wrapped__
