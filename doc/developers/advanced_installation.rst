
.. _advanced-installation:

==================================================
Installing the development version of pypads
==================================================

This section introduces how to install the **master branch** of pypads.
This can be done by either installing a nightly build or building from source.

.. _install_from_source:

Building from source
====================

Building from source is required to work on a contribution (bug fix, new
feature, code or documentation improvement).

.. _git_repo:

#. Use `Git <https://git-scm.com/>`_ to check out the latest source from the
   `pypads repository <https://github.com/padre-lab-eu/pypads>`_ on
   Github.::

        git clone git@github.com:padre-lab-eu/pypads.git  # add --depth 1 if your connection is slow
        cd pypads

   If you plan on submitting a pull-request, you should clone from your fork
   instead.

#. Install poetry tool for dependency managenment for your platform. See instructions in the `Official documentation <https://python-poetry.org/docs/#installation>`_.

#. Optional (but recommended): create and activate a dedicated virtualenv_
   or `conda environment`_.

#. Install build the project with poetry in :ref:`editable_mode`::

        poetry build & pip install ./dist/pypads-0.1.0.tar.gz .


Dependencies
------------

Runtime dependencies
~~~~~~~~~~~~~~~~~~~~

Scikit-learn requires the following dependencies both at build time and at
runtime:

- Python (>= 3.6),
- cloudpickle (>= 1.3.3),
- mlflow (>= 1.6.0),
- boltons (>= 19.3.0),
- loguru (>=0.4.1)

Those dependencies are **automatically installed by poetry** if they were missing
when building pypads from source.


Build dependencies
~~~~~~~~~~~~~~~~~~

Building Pypads also requires:

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

Some tests also require `numpy <https://numpy.org/>`_.


.. _virtualenv: https://docs.python.org/3/tutorial/venv.html
.. _conda environment: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html
