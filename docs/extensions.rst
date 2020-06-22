:globalsidebartoc: True

.. _extensions_menu:

===========================
Extensions and plugins
===========================

PyPads features a plugin system to extend its functionality. Currently following plugins are being developed.

pypads_padre
    Also called PadrePads introduces additional concepts of machine learning. While PyPads is fairly unopinionated about what it is logging PadrePads tries to impose some structure.

pypads_onto (unreleased)
    Also called OntoPads introduces ontology mappings to pypads. It is based on the other plugin PadrePads and will enable given concept unique references.

To enable an extension it just has to be installed into your active environment. If this fails due to some unexpected reason you can try to enable a plugin manually. In general this can look like this.


.. code-block:: python

    from pypads.app.base import PyPads
    from pypads_padre import activate
    activate()
    tracker = PyPads(autostart=True)


If you don't want to use an installed plugin, you can add the :literal:`disable_plugins` parameter to PyPads.

.. code-block:: python

    from pypads.app.base import PyPads
    tracker = PyPads(disable_plugins=["pypads_padre"], autostart=True)


|

.. toctree::
   :maxdepth: 2

   projects/pypads_padre
   projects/pypads_onto


