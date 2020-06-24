# PyPads
Building on the [MLFlow](https://github.com/mlflow/mlflow/) toolset this project aims to extend the functionality for MLFlow, increase the automation and therefore reduce the workload for the user. The production of structured results is an additional goal of the extension.

[![Documentation Status](https://readthedocs.org/projects/pypads/badge/?version=latest)](https://pypads.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/pypads.svg)](https://badge.fury.io/py/pypads)  

<!--- ![Build status](https://gitlab.padim.fim.uni-passau.de/RP-17-PaDReP/ontopads/badges/master/pipeline.svg) --->

# Intalling
This tool requires those libraries to work:

    Python (>= 3.6),
    cloudpickle (>= 1.3.3),
    mlflow (>= 1.6.0),
    boltons (>= 19.3.0),
    loguru (>=0.4.1)
    
PyPads only support python 3.6 and higher. To install pypads run this in you terminal

**Using source code**

First, you have to install **poetry** 

    pip install poetry
    poetry build (in the root folder of the repository pypads/)

This would create two files under pypads/dist that can be used to install,

    pip install dist/pypads-X.X.X.tar.gz
    OR
    pip install dist/pypads-X.X.X-py3-none-any.whl
    
 
**Using pip ([PyPi release](https://pypi.org/project/pypads/))**

The package can be found on PyPi in following [project](https://pypi.org/project/pypads/).

    pip install pypads

### Tests
The unit tests can be found under 'test/' and can be executed using

    poetry run pytest test/

# Documentation

For more information, look into the [official documentation of PyPads](https://pypads.readthedocs.io/en/latest/).

# Getting Started
         
### Usage example
pypads is easy to use. Just define what is needed to be tracked in the config and call PyPads.

A simple example looks like the following,
```python
from pypads.app.base import PyPads
# define the configuration, in this case we want to track the parameters, 
# outputs and the inputs of each called function included in the hooks (pypads_fit, pypads_predict)
hook_mappings = {
    "parameters": {"on": ["pypads_fit"]},
    "output": {"on": ["pypads_fit", "pypads_predict"]},
    "input": {"on": ["pypads_fit"]}
}
# A simple initialization of the class will activate the tracking
PyPads(hooks=hook_mappings)

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
        
        
The used hooks for each event are defined in the mapping file where each hook represents the functions to listen to.
Users can use regex for goruping functions and even provide paths to hook functions.
In the [sklearn mapping](pypads/bindings/resources/mapping/sklearn_0_19_1.yml) YAML file, an example entry would be:
```yaml
fragments:
  default_model:
    !!python/pPath __init__:
      hooks: "pypads_init"
    !!python/rSeg (fit|.fit_predict|fit_transform)$:
      hooks: "pypads_fit"
    !!python/rSeg (fit_predict|predict|score)$:
      hooks: "pypads_predict"
    !!python/rSeg (fit_transform|transform)$:
      hooks: "pypads_transform"

mappings:
  !!python/pPath sklearn:
    !!python/pPath base.BaseEstimator:
      ;default_model: ~
```
For instance, "pypads_fit" is an event listener on any fit, fit_predict and fit_transform call made by the tracked model class which is in this case **BaseEstimator** that most estimators inherits from.

Using no custom yaml types and no fragments the mapping file would be equal to following definition:
```yaml
mappings:
  :sklearn:
    :base.BaseEstimator:
        :__init__:
          hooks: "pypads_init"
        :{re:(fit|.fit_predict|fit_transform)$}:
          hooks: "pypads_fit"
        :{re:(fit_predict|predict|score)$}:
          hooks: "pypads_predict"
        {re:(fit_transform|transform)$}:
          hooks: "pypads_transform"
```

# Acknowledgement
This work has been partially funded by the **Bavarian Ministry of Economic Affairs, Regional Development and Energy** by means of the funding programm **"Internetkompetenzzentrum Ostbayern"** as well as by the **German Federal Ministry of Education and Research** in the project **"Provenance Analytics"** with grant agreement number *03PSIPT5C*.
