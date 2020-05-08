
.. _getting_started:

================
Getting started!
================

Usage
=====
.. _usage_example:

pypads is easy to use. Just define what is needed to be tracked in the config and call PyPads.

A simple example looks like the following.::

    from pypads.base import PyPads
    # define the configuration, in this case we want to track the parameters,
    # outputs and the inputs of each called function included in the hooks (pypads_fit, pypads_predict)
    config = {"events": {
        "parameters": {"on": ["pypads_fit"]},
        "output": {"on": ["pypads_fit", "pypads_predict"]},
        "input": {"on": ["pypads_fit"]}
    }}
    # A simple initialization of the class will activate the tracking
    PyPads(config=config)

    # An example
    from sklearn import datasets, metrics
    from sklearn.tree import DecisionTreeClassifier

    # load the iris datasets
    dataset = datasets.load_iris()

    # fit a model to the data
    model = DecisionTreeClassifier()
    model.fit(dataset.data, dataset.target) # pypads will track the parameters, output, and input of the model fit function.
    # get the predictions
    predicted = model.predict(dataset.data) # pypads will track only the output of the model predict function.


The used hooks for each event are defined in the mapping json file where each event includes the functions to listen to.

Mapping file example
====================

.. _mappingfile:

For the previous example, the sklearn mapping json file would look like the following.


.. literalinclude:: files/sklearn_example.json
    :language: JSON



For example, "pypads_fit" is an event listener on any **fit, fit_predict and fit_transform** function call made by any tracked class with those methods.

Defining a hook for an event
============================
.. _hooks:

A hook can be defined in the mapping file with 3 different ways.

#. Always::

    {
      "name": "sklearn classification metrics",
      "other_names": [],
      "implementation": {
        "sklearn": "sklearn.metrics.classification"
      },
      "hooks": {
        "pypads_metric": "always"
      }
    }

   This hook triggers always. If you annotate a module with this hook, all its functions and classes will be tracked.

#. QualNameHook::

    {
      "name": "sklearn classification metrics",
      "other_names": [],
      "implementation": {
        "sklearn": "sklearn.metrics.classification"
      },
      "hooks": {
        "pypads_metric": ["f1_score"]
      }
    }

   Tracks function with a name matching the given Regex.

#. PackageNameHook::

    {
      "name": "sklearn classification metrics",
      "other_names": [],
      "implementation": {
        "sklearn": "sklearn.metrics"
      },
      "hooks": {
        "pypads_metric": [{"type": "package_name", "name":".*classification.*"}]
      }
    }

   Tracks all attributes of the module where "package_name" is matching Regex.

Define an event
===============
.. _events:

Once the hooks are defined, they are then linked to the events we want them to trigger. Following the example below, the hook **pypads_metric** will be linked to an event we call
**Metrics** for example. This is done via passing a dictionary as the parameter **config** to the :ref:`PyPads class <base_class>`::

    config = {"events": {
                        "Metrics" : {"on": ["pypads_metrics"]}
                        }
             }



PyPads loggers
==============
.. _logging:

PyPads has a set of built-in logging functions that are mapped by default to some pre-defined events. Check the default setting of PyPads :ref:`here <default_setting>`.
The user can also define custom logging functions for custom events. Details on how to do that can be found (:ref:`here <loggingfns>`).