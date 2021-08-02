..

PyPaDS: Documentation!
==================================

`PyPaDS`_ aims to make logging as easy as possible for the user. The production of structured results is an
additional goal of the extension.

.. _PyPaDS: https://github.com/padre-lab-eu/pypads

.. note::
    A larger update regarding the mapping files was released recently. Mapping files are now based on YML and are more hook centric. Read more about mapping files :ref:`here <mapping_files>`.

Install PyPads
--------------

Logging your experiments manually can be overwhelming and exhaustive? PyPads is a tool to help automate logging as much information as possible by
tracking the libraries of your choice.

* **Installing PyPads**:
   :ref:`With pip <install_official_release>` |
   :ref:`From source <install_from_source>`

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Install PyPads:

   install


Getting started
---------------

Learn more about how to use pypads, configuring your tracking events and hooks, mapping your custom logging function
and some of the core features of PyPads.

* **Usage example**
   :ref:`Decision Tree Iris classification <usage_example>`

* **Mapping file example for Scikit-learn**
   A :ref:`mapping file <mappingfile>` is where we define the classes and functions to be tracked from the library of our choice. It includes the defined hooks.
* **Hooks and events**
   - :ref:`Events <events>` are defined primarily by listeners which are, in our case, **hooks**. When triggered, the corresponding loggers are called. Logging functions are linked to these events via a mapping dictionary passed to the :ref:`base class <base_class>`.
   - :ref:`Hooks <hooks>` help the user to define what triggers those events (e.g. what functions or classes should trigger a specific event).
* **Loggers**
   Logging functions are functions called around when any tracked method or class triggers their corresponding event. Mapping events to logging functions is done by passing a dictionary **mapping** as a parameter to the :ref:`PyPads class <base_class>`.

The following tables show the default loggers of pypads.

   * Event Based loggers
      .. list-table::
         :widths: 10 10 25 25
         :header-rows: 1

         * - Logger
           - Event
           - Hook
           - Description
         * - LogInit
           - init
           - 'pypads_init'
           - Debugging purposes
         * - Log
           - log
           - 'pypads_log'
           - Debugging purposes
         * - Parameters
           - parameters
           - 'pypads_fit'
           - tracks parameters of the tracked function call
         * - Cpu,Ram,Disk
           - hardware
           - 'pypads_fit'
           - track usage information, properties and other info on CPU, Memory and Disk.
         * - Input
           - input
           - 'pypads_fit'
           - tracks the input parameters of the current tracked function call.
         * - Output
           - output
           - 'pypads_predict', 'pypads_fit'
           - Logs the output of the current tracked function call.
         * - Metric
           - metric
           - 'pypads_metric'
           - tracks the output of the tracked metric function.
         * - PipelineTracker
           - pipeline
           - 'pypads_fit','pypads_predict', 'pypads_transform', 'pypads_metrics'
           - tracks the workflow of execution of the different pipeline elements of the experiment.

   * Pre/Post run loggers
      .. list-table::
         :widths: 10 10 25
         :header-rows: 1

         * - Logger
           - Pre/Post
           - Description
         * - IGit
           - Pre
           - Source code management and tracking
         * - ISystem
           - Pre
           - System information (os,version,machine...)
         * - ICpu
           - Pre
           - Cpu information (Nbr of cores, max/min frequency)
         * - IRam
           - Pre
           - Memory information (Total RAM, SWAP)
         * - IDisk
           - Pre
           - Disk information (disk total space)
         * - IPid
           - Pre
           - Process information (ID, command, cpu usage, memory usage)
         * - ISocketInfo
           - Pre
           - Network information (hostname, ip address)
         * - IMacAddress
           - Pre
           - Mac address

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Getting started:

   getting_started

PyPads
------
.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: PyPads:

   classes/base_class
   classes/logging_fns
   classes/utilities
   mapping_files

Extensions
----------------
- **PaDRe-Pads** is a tool that builds on PyPads and add some semantics to the tracked data of Machine learning experiments. See the `padre-pads documentation <https://github.com/padre-lab-eu/padre-pads>`_.

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Extensions and Plugins:

   extensions


Related Projects
----------------
- **PyPadre** is the predecessor of PadrePads. Its development has been discontinued.

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Related Projects:

   related_projects

.. include:: ../CHANGELOG.rst

About Us
--------
This work has been developed within the **Data Science Chair** of the University of Passau.
It has been partially funded by the **Bavarian Ministry of Economic Affairs, Regional Development and Energy** by means
of the funding programm "**Internetkompetenzzentrum Ostbayern**" as well as by the **German Federal Ministry of Education
and Research** in the project "**Provenance Analytics**" with grant agreement number 03PSIPT5C.

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: About Us:

   about
