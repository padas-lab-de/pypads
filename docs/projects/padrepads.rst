.. _padrepads:

=========
PadrePads
=========

Installing the latest release with pip
======================================

The lastest stable version of padrepads can be downloaded and installed from `PyPi <https://pypi.org/project/padrepads/>`_::

   pip install padrepads


Note that in order to avoid potential conflicts with other packages it is
strongly recommended to use a virtual environment, e.g. python3 ``virtualenv``
(see `python3 virtualenv documentation
<https://docs.python.org/3/tutorial/venv.html>`_) or `conda environments
<https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html>`_.

.. warning::

    PadrePads requires Python 3.6 or newer.

Installing padrepads from source
================================

This section introduces how to install the **master branch** of padrepads.
This can be done by building from source.


Building from source
--------------------

Building from source is required to work on a contribution (bug fix, new
feature, code or documentation improvement).


#. Use `Git <https://git-scm.com/>`_ to check out the latest source from the
   `pypads repository <https://github.com/padre-lab-eu/padre-pads>`_ on
   Github.::

        git clone git@github.com:padre-lab-eu/padre-pads.git  # add --depth 1 if your connection is slow
        cd padre-pads

   If you plan on submitting a pull-request, you should clone from your fork
   instead.

#. Install poetry tool for dependency managenment for your platform. See instructions in the `Official documentation <https://python-poetry.org/docs/#installation>`_.::

        pip install poetry

#. Optional (but recommended): create and activate a dedicated virtualenv_
   or `conda environment`_.

#. Build the project with poetry, this will generate a whl and a tar file under dist/::

        poetry build (in the root folder of the repository)

#. Install padrepads using one of the two generated files::

        pip install dist/padrepads-X.X.X.tar.gz
        OR
        pip install dist/padrepads-X.X.X-py3-none-any.whl

Dependencies
------------

Runtime dependencies
~~~~~~~~~~~~~~~~~~~~

Pypads requires the following dependencies both at build time and at
runtime:

- Python (>= 3.6),
- Pypads (>= 1.8.0)


Build dependencies
~~~~~~~~~~~~~~~~~~

Building padrepads also requires:

- Poetry >= 0.12.


Test dependencies
~~~~~~~~~~~~~~~~~

Running tests requires:

- pytest >= 5.2.5,
- scikit-learn >= 0.21.3,
- tensorflow >= 2.0.0b1,
- psutil >= 5.7.0,
- networkx >= 2.4,
- keras >= 2.3.1.
- PyTorch >= 1.4.0
- torchvision >= 0.5.0


.. _virtualenv: https://docs.python.org/3/tutorial/venv.html
.. _conda environment: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html

Concepts
========

PadrePads builds upon pypads when it comes to tracking, but it also adds a layer of loggers that tracks semantic information from experiments executions.

Dataset tracking
----------------

PadrePads have a dataset logger that tries to identify the object returned by the tracked function hooked with 'pypads_dataset'.
After collecting as mush metadata on this object, padrepads then dumps it on disk along with the metadata and link to the current run ID.

The currently supported dataset providers by padrepads::

    - Scikit-learn (sklearn.datasets).
    - Keras datasets.
    - torchvision datasets.

Split tracking
--------------

Decisions tracking
------------------

Grid Search
-----------
