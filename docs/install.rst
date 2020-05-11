.. _installation-instructions:

==============
How To Install
==============

There are different ways to install pypads:

  * :ref:`Install the latest official release <install_official_release>`. This
    is the best approach for most users. It will provide a stable version
    and pre-built packages are available for most platforms.

  * :ref:`Building the package from source
    <install_from_source>`. This is best for users who want the
    latest features and aren't afraid of running
    brand-new code. This is also needed for users who wish to contribute to the
    project.


.. _install_official_release:

Installing the latest release with pip
======================================

The lastest stable version of pypads can be downloaded and installed from `PyPi <https://pypi.org/project/pypads/>`_::

   pip install pypads


Note that in order to avoid potential conflicts with other packages it is
strongly recommended to use a virtual environment, e.g. python3 ``virtualenv``
(see `python3 virtualenv documentation
<https://docs.python.org/3/tutorial/venv.html>`_) or `conda environments
<https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html>`_.

Using an isolated environment makes possible to install a specific version of
pypads and its dependencies independently of any previously installed
Python packages.
In particular under Linux is it discouraged to install pip packages alongside
the packages managed by the package manager of the distribution
(apt, dnf, pacman...).

Note that you should always remember to activate the environment of your choice
prior to running any Python command whenever you start a new terminal session.


.. warning::

    Pypads requires Python 3.6 or newer.

.. _advanced-installation:


Installing pypads from source
=============================

This section introduces how to install the **master branch** of pypads.
This can be done by building from source.

.. _install_from_source:

Building from source
--------------------

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

#. Install poetry tool for dependency managenment for your platform. See instructions in the `Official documentation <https://python-poetry.org/docs/#installation>`_.::

        pip install poetry

#. Optional (but recommended): create and activate a dedicated virtualenv_
   or `conda environment`_.

#. Build the project with poetry, this will generate a whl and a tar file under dist/::

        poetry build

#. Install pypads using one of the two generated files::

        pip install dist/pypads-X.X.X.tar.gz
        OR
        pip install dist/pypads-X.X.X-py3-none-any.whl

If the package is available on pypi but can't be found with poetry you might want to delete your local poetry cache :

    poetry cache clear --all pypi

Dependencies
------------

Runtime dependencies
~~~~~~~~~~~~~~~~~~~~

Pypads requires the following dependencies both at build time and at
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

Building PyPads also requires:

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