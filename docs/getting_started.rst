.. _getting_started:

================
Getting started with PyPads
================

.. meta::
   :description lang=en: Get started tracking experiments with PyPads.

PyPads is a tracking framework for your python programs. It implements an infrastructure featuring the possibilities for:

* Community driven mapping files
* Logging injection by importlib extension
* Timekeeping
* Full access to the current state in logging functions
* Prefabricated tracking functions and formats
* Data and control flow manipulation with actuators
* Run based data caching for loggers

The framework was developed for machine learning experiments and is based on mlflow. The main focus for PyPads is based in its ulterior, but pythonic manner of use. PyPads aims to deliver a way to harmonize results of a multitude of libraries in a structured way, while stepping out of the way if needed. Most dependencies of PyPads are to be considered as optional and are only used to extend on more sophisticated logging functions.

In its core app, PyPads allows for registering plugin :ref:`extensions <extensions>`. These can be used to define packages introducing new loggers, validators, actuators, decorators etc.


Quick start
-----------

Install PyPads assuming Python 3 is already installed:

.. code-block:: bash

    $ pip install pypads


Usage
====================
.. _usage_example:

Activating PyPads for tracking in its default setting is as easy as adding two lines to your experiment.

A simple example looks like the following.

.. code-block:: python

    from pypads.app.base import PyPads
    PyPads(autostart=True)

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


Results
====================
By default results can be found in the :literal:`.mlruns` folder in the home directory of the executing user. While this can be changed when initializing the app, you can also specify the environment variable :literal:`MLFLOW_PATH` to define a custom location.

Concepts
----------------

PyPads includes a set of concepts, of which some are to be followed because of technical reasons, while others only impose semantical meaning.


Actuators
=========
Actuators are features of PyPads manipulating experiments. When using an actuator the result of the experiment may be or is impacted. Actuators can include changes to the underlying machine learning code, setup and more. An exemplary actuator is an actuator enforcing a random seed setup. Custom, new or other actuators can be added to an IActuators plugin exposing them to PyPads.

.. code-block:: python

    @actuator
    def set_random_seed(self, seed=None):
        # Set seed if needed
        if seed is None:
            import random
            # Numpy only allows for a max value of 2**32 - 1
            seed = random.randrange(2 ** 32 - 1)
        self.pypads.cache.run_add('seed', seed)

        from pypads.injections.analysis.randomness import set_random_seed
        set_random_seed(seed)

To call an actuator you can use the app.

.. code-block:: python

    from pypads.app.base import PyPads
    tracker = PyPads(autostart=True)
    tracker.actuators.set_random_see(seed=1)


API
=========
The PyPads API delivers standard functionality of PyPads. This also pipes some of mlflow features. You can start, stop runs, log artifacts, metrics or parameters, set tags and write meta information about them. Additionally the PyPads API inroduces setup and teardown (also called pre and post run) functions to be called and also to manually mark functions for tracking. A full documentation can be found :ref:`here <api>`. To call the api you can use the app.

.. code-block:: python

    from pypads.app.base import PyPads
    tracker = PyPads(autostart=True)
    tracker.api.set_tag("foo", "bar")


Validators
=========
Validators are to be used if the experimental status or code has to be checked on some properties. These should normally not log anything, but a validation report. A validation report should be an optional tag or at max a text file. In general validators should inform the user on runtime about errors and problems. It is planned to add the possibility to interrupt an execution if validators fail in the future. Some validators will be logging functions bound to library functions. An examplary validator which will want to be bound to the usage of pytorch is the determinism check for pytorch.

.. code-block:: python

    @validator
    def determinism(self):
        check_determinism()

To call the api you can use the app.

.. code-block:: python

    from pypads.app.base import PyPads
    tracker = PyPads(autostart=True)
    tracker.validators.set_tag("foo", "bar")


Setup / Teardown functions
=========
Setup or teardown functions are to be called when a run starts or ends. These mostly are used to log meta information about the experiment including data about git, hardware and the environment. A list of currently defined decorators can be found :ref:`here <prepost>`.

.. code-block:: python

    class ICpu(PreRunFunction):

    @staticmethod
    def _needed_packages():
        return ["psutil"]

    def _call(self, pads, *args, **kwargs):
        import psutil
        pads.api.set_tag("pypads.system.cpu.physical_cores", psutil.cpu_count(logical=False))
        pads.api.set_tag("pypads.system.cpu.total_cores", psutil.cpu_count(logical=True))
        freq = psutil.cpu_freq()
        pads.api.set_tag("pypads.system.cpu.max_freq", f"{freq.max:2f}Mhz")
        pads.api.set_tag("pypads.system.cpu.min_freq", f"{freq.min:2f}Mhz")

Configuring setup or teardown functions can be done via the app constructor or api.

.. code-block:: python

    from pypads.app.base import PyPads
    tracker = PyPads(setup_fns=[ICpu()], autostart=True)
    # tracker.api.register_setup("custom_cpu", ICpu())


MappingFiles
=========
Mapping files deliver hooks into libraries to trigger tracking functionality. They are written in yml and defining a syntax to markup functions, classes and modules.


Decorators
=========
Decorators can be used instead of a mapping file to denote hooks in code. Because most libraries are not to be changed directly they are currently used sparingly. In PyPads defined decorators can be found :ref:`here <decorators>`.


Logging functions
=========
Logging functions are the generic functions performing tracking tasks bound to hooked functions of libraries. Everything not fitting into other concepts is just called logging function. Following function would track the input to the hooked function.

.. code-block:: python

    class Input(LoggingFunction):
    """
    Function logging the input parameters of the current pipeline object function call.
    """

    def __pre__(self, ctx, *args, _pypads_write_format=WriteFormats.pickle, _pypads_env: LoggingEnv, **kwargs):
        """
        :param ctx:
        :param args:
        :param _pypads_write_format:
        :param kwargs:
        :return:
        """
        for i in range(len(args)):
            arg = args[i]
            name = os.path.join(_pypads_env.call.to_folder(),
                                "args",
                                str(i) + "_" + str(id(_pypads_env.callback)))
            try_write_artifact(name, arg, _pypads_write_format)

        for (k, v) in kwargs.items():
            name = os.path.join(_pypads_env.call.to_folder(),
                                "kwargs",
                                str(k) + "_" + str(id(_pypads_env.callback)))
            try_write_artifact(name, v, _pypads_write_format)

Configuring logging functions can be achieved by providing mappings to the constructor of the app. Mapping files provide hooks (generally prepended by "pypads" in their naming) and logging functions are mapped to events. A hook can subsequently trigger multiple events and thus logging functions. To pass an event to function mapping a simple dict can be used.

.. code-block:: python

    from pypads.app.base import PyPads
    event_function_mapping = {
        "parameters": Parameters(),
        "output": Output(_pypads_write_format=WriteFormats.text.name),
        "input": Input(_pypads_write_format=WriteFormats.text.name)
    }
    tracker = PyPads(events=event_function_mapping, autostart=True)

Additionally a hook to event mapping can be defined.

.. code-block:: python

    from pypads.app.base import PyPads
    hook_event_mapping = {
        "parameters": {"on": ["pypads_fit"]},
        "output": {"on": ["pypads_fit", "pypads_predict"]},
        "input": {"on": ["pypads_fit"], "with": {"_pypads_write_format": WriteFormats.text.name}},
    }
    tracker = PyPads(hooks=hook_event_mapping, autostart=True)

Defining hooks can be done via api, mappings, mapping files or decorators. Decorators are a sensible approach for local custom code.

.. code-block:: python

    from pypads.app.base import PyPads
    tracker = PyPads(autostart=True)

    @tracker.decorator.track(event="pypads_fit")
    def fit_function_to_track(foo: str):
        return foo + "bar"

The same holds true for api based tracking.

.. code-block:: python

    from pypads.app.base import PyPads
    tracker = PyPads(autostart=True)

    def fit_function_to_track(foo: str):
        return foo + "bar"

    tracker.api.track(ctx=get_class_that_defined_method(fit_function_to_track), fn=fit_function_to_track, hooks=["pypads_fit"])

Mapping files or mappings are a more permanent, shareable and modular approach.

.. code-block:: python

    from pypads.app.base import PyPads
    serialized_mapping = """
        metadata:
          author: "Thomas Weißgerber"
          version: "0.0.1"
          library:
            name: "test_foo"
            version: "0.1"

        mappings:
            :my_package.my_class.fit_function_to_track:
                    events: "pypads_fit"
        """

    tracker = PyPads(mapping=SerializedMapping("test_foo", serialized_mapping), autostart=True)

    def fit_function_to_track(foo: str):
        return foo + "bar"


Check points
=========
Check points are currently not implemented. They will introduce a structured way to denote cache able states. By defining check points we hope to be able to define marks from which an experiment can be rerun in the future.


Examples
--------

Sklearn DecisionTree example
====================
Following shows how PyPads can be used to track the parameters, input and output of a sklearn experiment.

.. code-block:: python

    # define the configuration, in this case we want to track the parameters,
    # outputs and the inputs of each called function included in the hooks (pypads_fit, pypads_predict)
    events = {
        "parameters": {"on": ["pypads_fit"]},
        "output": {"on": ["pypads_fit", "pypads_predict"]},
        "input": {"on": ["pypads_fit"]}
    }
    # A simple initialization of the class will activate the tracking
    PyPads(events=events)

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

The used hooks for each event are defined in the mapping yml file where each event includes the functions to listen to.


Mapping file example
====================

.. _mappingfile:

For the previous example, the sklearn mapping yml file would look like the following.


.. literalinclude:: files/sklearn_example.yml
    :language: YAML



For example, "pypads_fit" is an event listener on any **fit, fit_predict and fit_transform** function call made by any tracked class with those methods.


Defining a hook for an event
============================
.. _hooks:

A hook can be defined in the mapping file via the "hooks" attribute. It is composed of the given name and path defined by the keys in the yml file. Muliple hooks can use the same name and therefore trigger the same functions.


Define an event
===============

.. _events:

Once the hooks are defined, they are then linked to the events we want them to trigger. Following the example below, the hook **pypads_metric** will be linked to an event we call
**Metrics** for example. This is done via passing a dictionary as the parameter **config** to the :ref:`PyPads class <base_class>`

.. code-block:: python

    hook_mappings = {
                "Metrics" : {"on": ["pypads_metrics"]}
             }


PyPads loggers
==============
.. _logging:

PyPads has a set of built-in logging functions that are mapped by default to some pre-defined events. Check the default setting of PyPads :ref:`here <default_setting>`.
The user can also define custom logging functions for custom events. Details on how to do that can be found :ref:`here <loggingfns>`.


External resources
------------------

Currently there are unfortunately not too many external resources available fo PyPads. Additional examples are to be
added in the next steps of the road map. You can find an IPython Notebook and an Code example on these repositories.


TODO Please add links to two repositories with example code (We can use the stuff for the data science lab)
