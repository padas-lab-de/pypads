.. _mapping_files:

=============
Mapping Files
=============

PyPads using the concept of mapping files to track which functions should be logged. These files are written in YAML.
YAML (YAML Ain't A Markup Language) is a human readable data serialization language. YAML has features such as comments
and anchors these features make it desirable.


The mapping file can be divided broadly into different parts like metadata, fragments and mappings. Each section is
explained in detail below. Following excerpts show possible mapping files. While the keras file uses implicit syntax for the path matchers marked by a prepending :literal:`:`, the sklearn version depicts how to use YAML typing with :literal:`!!python/pPath`, :literal:`!!python/rSeg` or :literal:`!!python/pSeg`.

.. literalinclude:: files/keras.2_3_1.yml
    :language: YAML

.. literalinclude:: files/sklearn_0_19_1.yml
    :language: YAML

.. _metadata:
Metadata
    The metadata part contains information about the author, the mapping file version and the library information.
    The mapping file version is required so that a change in the tracking functionalities can be easily traced to the version
    of the mapping file. Even while having the same library version, a user can modify the mapping file to track additional
    functions of the library or remove some tracking functionalities. Such changes need to be handled to provide better
    experiment tracking and reproducibility. PyPads does this via versioning of the mapping file. Another tag called
    "library" contains information about the library which the mapping file addresses such as the name of the library and
    the version of the library. This metadata section helps PyPads track different versions of libraries without them having
    a conflict.

.. code-block:: YAML

    metadata:
      author: "Thomas Weißgerber"
      version: "0.1.0"
      library:
        name: "sklearn"
        version: "0.19.1"


.. _fragments:
Fragments
    Repeated patterns in the library can be included in the fragments section of the mappings file. Fragments allows users
    to link functions across classes. For example, in scikit-learn the fit function is a function for fitting the estimators.
    All classification/regression estimators will have a fit function. In such a scenario, the user does not have to write
    mappings for each and every estimator. Instead, the user can add the function to the fragments part and PyPads will
    automatically log those functions.

.. code-block:: YAML

    fragments:
      default_model:
        .__init__:
          events: "pypads_init"
        .{re:(fit|.fit_predict|fit_transform)$}:
          events: "pypads_fit"


.. _mappings:
Mappings
    This part in the mapping file gives information to PyPads about the functions to track. In the example, we use the
    sklearn base estimator to encompass all logging functionalities from a single point. The user can add other classes as
    shown with the Decision Tree Classifier. By doing this the user also has to provide all the hyperparameters so that
    PyPads knows what to track. For each hyperparameter the user also has to provide the name of the hyperparameter,
    whether it is optional or not, its description and so forth.

Concepts
=========
PyPads mapping files contain keys called concepts. When creating a main key in the mappings file, it could be anything
such as a metric, a dataset, splitting strategy, an algorithm and so forth. The concepts key present within the main key
links the main key to previously determined categories such as metric, dataset or algorithm to name a few. This helps
PyPads recognize what type the main key is and how to process it.

Notations
=========

.. _notations:
PyPads can accept different notations through the YAML parser. Users can use the power of regular expressions to specify
function groups that should trigger specific events. Here in the below given example, we hook all functions in
sklearn.metrics.classification to "pypads_metric". We also inform PyPads that all functions of this form are an instance
of sklearn provided metrics using the concepts key.

.. code-block:: YAML

    mappings:
      sklearn:
        .metrics.classification.{re:.*}:
           data:
             concepts: ["Sklearn provided metric"]
             events: "pypads_metric"


Adding a new mapping file
=========================

When a user wants to add their own mapping file, they have to follow the following steps
# Create a YAML mapping file in the path pypads/bindings/resources/mapping with the appropriate name and version number
# Add a metadata part containing information about the author, version of the mapping file and library
# Add fragments if a general function name is present. You can use regex to specify the patterns
# Add mappings for metrics, datasets etc is they are present
# PyPads will pick up the information when it is restarted.
