.. _installation-instructions:

=======================
Installing pypads
=======================

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

Installing the latest release
=============================

.. This quickstart installation is a hack of the scikit-learn.
   See the original https://github.com/scikit-learn/scikit-learn/blob/master/doc/install.rst


.. raw:: html

  <div class="install">
       <strong>Operating System</strong>
          <input type="radio" name="os" id="quickstart-win" checked>
          <label for="quickstart-win">Windows</label>
          <input type="radio" name="os" id="quickstart-mac">
          <label for="quickstart-mac">macOS</label>
          <input type="radio" name="os" id="quickstart-lin">
          <label for="quickstart-lin">Linux</label><br />
       <strong>Packager</strong>
          <input type="radio" name="packager" id="quickstart-pip" checked>
          <label for="quickstart-pip">pip</label>
          <input type="radio" name="packager" id="quickstart-conda">
          <label for="quickstart-conda">conda</label><br />
          <input type="checkbox" name="config" id="quickstart-venv">
          <label for="quickstart-venv"></label>
       </span>

.. raw:: html

       <div>
         <span class="pp-expandable" data-packager="pip" data-os="windows">Install the 64bit version of Python 3, for instance from <a href="https://www.python.org/">https://www.python.org</a>.</span
         ><span class="pp-expandable" data-packager="pip" data-os="mac">Install Python 3 using <a href="https://brew.sh/">homebrew</a> (<code>brew install python</code>) or by manually installing the package from <a href="https://www.python.org">https://www.python.org</a>.</span
         ><span class="pp-expandable" data-packager="pip" data-os="linux">Install python3 and python3-pip using the package manager of the Linux Distribution.</span
         ><span class="pp-expandable" data-packager="conda"><a href="https://docs.conda.io/projects/conda/en/latest/user-guide/install/">Install conda</a> (no administrator permission required).</span>
       </div>

Then run:

.. raw:: html

       <div class="highlight"><pre><code
        ><span class="pp-expandable" data-packager="pip" data-os="linux" data-venv="">python3 -m venv pypads-venv</span
        ><span class="pp-expandable" data-packager="pip" data-os="windows" data-venv="">python -m venv pypads-venv</span
        ><span class="pp-expandable" data-packager="pip" data-os="mac" data-venv="">python -m venv pypads-venv</span
        ><span class="pp-expandable" data-packager="pip" data-os="linux" data-venv="">source pypads-venv/bin/activate</span
        ><span class="pp-expandable" data-packager="pip" data-os="mac" data-venv="">source pypads-venv/bin/activate</span
        ><span class="pp-expandable" data-packager="pip" data-os="windows" data-venv="">pypads-venv\Scripts\activate</span
        ><span class="pp-expandable" data-packager="pip" data-venv="">pip install pypads</span
        ><span class="pp-expandable" data-packager="pip" data-os="mac" data-venv="no">pip install -U pypads</span
        ><span class="pp-expandable" data-packager="pip" data-os="windows" data-venv="no">pip install -U pypads</span
        ><span class="pp-expandable" data-packager="pip" data-os="linux" data-venv="no">pip3 install -U pypads</span
       ></code></pre></div>


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

