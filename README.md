# PyPads
Building on the [MLFlow](https://github.com/mlflow/mlflow/) toolset this project aims to extend the functionality for MLFlow, increase the automation and therefore reduce the workload for the user. The production of structured results is an additional goal of the extension.

# Concept
Logging results of machine learning workflows often shares similar structures and goals. You might want to track parameteres, loss functions, metrics or other characteristic numbers. While the produced output shares a lot of concepts and could be standardized, implementations are diverse and integrating them or their autologging functionality into such a standard needs manual labour. Each and every version of a library might change internal structures and hard coding interfaces can need intesive work. Pypads aims to feature following main techniques to handle autologging and standardization efforts:
- **Automatic metric tracking:** TODO
- **Automatic execution tracking:** TODO 
- **Community driven mapping files:** A means to log data from python libaries like sklearn. Interfaces are not added directly to MLFlows, but derived from versioned mapping files of frameworks.
- **Output standardization:** TODO
- **Dataset management:** TODO

# Use Cases
- **Explorative logging**: TODO
- **Pipeline extraction**: TODO
- **Inter experiment comparision**: TODO

# Getting started
This tool requires those libraries to work:

    mlflow>=1.4.0
    boltons>=19.3.0
To install pypads from source, clone the source code repository and run
   
    python setup.py install
        
### Usage
pypads is easy to use. Just define what is needed to be tracked in the config and call PyPads.

A simple example looks like the following,
```python
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
```
        
The used hooks for each event are defined in the mapping json file where each event includes the functions to listen to.
In the example of sklearn mapping json file, we have:

    "default_hooks": {
        "modules": {
          "fns": {}
        },
        "classes": {
          "fns": {
            "pypads_fit": [
              "fit",
              "fit_predict",
              "fit_transform"
            ],
            "pypads_predict": [
              "fit_predict",
              "predict",
              "score"
            ],
            "pypads_transform": [
              "fit_transform",
              "transform"
            ]
          }
        },
        "fns": {
          "pypads_metric": [
            "f1_score"
          ]
        }
      }

For example, "pypads_fit" is an event listener on any fit, fit_predict and fit_transform call made by the tracked model class.

#### Always
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

#### QualNameHook
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

#### PackageNameHook
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
Tracks all attr on module where package name is matching Regex.

### PyPads class
As we have seen, a simple initialization of the class at the top of your code activate the tracking for libraries that has a mapping file defining the algorithms to track.

Beside the configuration, **PyPads** takes other optional arguments.
```python        
class PyPads(uri=None, name=None, mapping=None, config=None, mod_globals=None)
```
[Source](https://github.com/padre-lab-eu/pypads/blob/0cb9f9bd5dff7753f7c47dc691d41edd0426a90a/pypads/base.py#L141)

**Parameters**:
> **uri : string, optional (default=None)** <br> Address of local or remote tracking server that **MLflow** uses to record runs. If None, then it tries to get the environment variable **'MLFLOW_PATH'** or the **'HOMEPATH'** of the user. 
> 
> **name : string, optional (default=None)** <br> Name of the **MLflow** experiment to track.
>
> **mapping : dict, optional (default=None)** <br> Mapping to the logging functions to use for the tracking of the events. If None, then a DEFAULT_MAPPING is used which allow to log parameters, outputs or inputs.
>
> **config : dict, optional (default=None)** <br> A dictionary that maps the events defined in PyPads mapping files with the logging functions.
>
> **mod_globals : object, optional (default=None)** <br> globals() object used to 'duckpunch' already loaded classes.
# Scientific work disclaimer
This was created in scope of scientific work of the Data Science Chair at the University of Passau. If you want to use this tool or any of its resources in your scientific work include a citation.
