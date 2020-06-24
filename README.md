
# PyPads
Building on the [MLFlow](https://github.com/mlflow/mlflow/) toolset this project aims to extend the functionality for MLFlow, increase the automation and therefore reduce the workload for the user. The production of structured results is an additional goal of the extension.

[![Documentation Status](https://readthedocs.org/projects/pypads/badge/?version=latest)](https://pypads.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/pypads.svg)](https://badge.fury.io/py/pypads)  

![Build status](https://gitlab.padim.fim.uni-passau.de/RP-17-PaDReP/ontopads/badges/master/pipeline.svg)

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
      data:
        concepts: ["algorithm"]
    !!python/pPath metrics.classification:
      !!python/rSeg .*:
        hooks: "pypads_metric"
        data:
          concepts: ["Sklearn provided metric"]
```
For instance, "pypads_fit" is an event listener on any fit, fit_predict and fit_transform call made by the tracked model class which is in this case **BaseEstimator** that most estimators inherits from.

### Defining hooks
Hooks are what triggers an "event" which is associated to one or more logger function in the mapping.

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
Tracks function with a name matching the given expression by compiling a regex expression.

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
Tracks all attribute on module where package name is matching Regex.

### Default Events, Hooks and Logging Functions

The default configuration of events/hooks and logging functions for PyPads:

    DEFAULT_CONFIG = {"events": {
    "init": {"on": ["pypads_init"]},
    "parameters": {"on": ["pypads_fit"]},
    "hardware": {"on": ["pypads_fit"]},
    "output": {"on": ["pypads_fit", "pypads_predict"]},
    "input": {"on": ["pypads_fit"], "with": {"_pypads_write_format": WriteFormats.text.name}},
    "metric": {"on": ["pypads_metric"]},
    "pipeline": {"on": ["pypads_fit", "pypads_predict", "pypads_transform", "pypads_metric"]},
    "log": {"on": ["pypads_log"]}
    },
        "recursion_identity": False,
        "recursion_depth": -1,
        "log_on_failure": True}
    
    DEFAULT_LOGGING_FNS = {
    "parameters": Parameters(),
    "output": Output(_pypads_write_format=WriteFormats.text.name),
    "input": Input(_pypads_write_format=WriteFormats.text.name),
    "hardware": {Cpu(), Ram(), Disk()},
    "metric": Metric(),
    "autolog": MlflowAutologger(),
    "pipeline": PipelineTracker(_pypads_pipeline_type="normal", _pypads_pipeline_args=False),
    "log": Log(),
    "init": LogInit()

Loggers in pypads goes into three categories. Pre, Post run loggers and event based loggers.

* Event based loggers:

| Logger  | Event | Hook | Description
| :-------------: |:----------:|: -----------:| ----------------|
| LogInit  | init | 'pypads_init'| Debugging purposes |
| Log  | log | 'pypads_log'| Debugging purposes |
| Parameters  |  parameters | 'pypads_fit'| tracks parameters of the tracked function call |
| Cpu,Ram,Disk  |  hardware | 'pypads_fit'| track usage information, properties and other info on CPU, Memory and Disk. |
| Input  |  input | 'pypads_fit' |tracks the input parameters of the current tracked function call. | 
| Output  | output | 'pypads_predict', 'pypads_fit' |Logs the output of the current tracked function call.| 
| Metric  | metric | 'pypads_metric' |tracks the output of the tracked metric function. | 
| PipelineTracker  | pipeline | 'pypads_fit','pypads_predict', 'pypads_transform', 'pypads_metrics'|tracks the workflow of execution of the different pipeline elements of the experiment.| 

* Pre/Post run loggers:

| Logger  | Pre/Post | Description
| :-------------:|: -----------:| ----------------|
| IGit  | Pre | Source code management and tracking|
| ISystem  | Pre | System information (os,version,machine...)|
| ICpu  |  Pre | Cpu information (Nbr of cores, max/min frequency)|
| IRam  |  Pre | Memory information (Total RAM, SWAP)|
| IDisk  |  Pre | Disk information (disk total space)| 
| IPid  | Pre | Process information (ID, command, cpu usage, memory usage)| 
| ISocketInfo  | Pre | Network information (hostname, ip address)| 
| IMacAddress  | Pre | Mac address |

# Concept
Logging results of machine learning workflows often shares similar structures and goals. You might want to track parameteres, loss functions, metrics or other characteristic numbers. While the produced output shares a lot of concepts and could be standardized, implementations are diverse and integrating them or their autologging functionality into such a standard needs manual labour. Each and every version of a library might change internal structures and hard coding interfaces can need intesive work. Pypads aims to feature following main techniques to handle autologging and standardization efforts:
- **Automatic metric tracking:** TODO
- **Automatic execution tracking:** TODO 
- **Community driven mapping files:** A means to log data from python libaries like sklearn. Interfaces are not added directly to MLFlows, but derived from versioned mapping files of frameworks.
- **Output standardization:** TODO


### PyPads class
As we have seen, a simple initialization of the class at the top of your code activate the tracking for libraries that has a mapping file defining the algorithms to track.

Beside the configuration, **PyPads** takes other optional arguments.
```python        
class PyPads(uri=None, name=None, mapping_paths=None, mapping=None, init_run_fns=None,
                 include_default_mappings=True,
                 logging_fns=None, config=None, reload_modules=False, reload_warnings=True, clear_imports=False,
                 affected_modules=None)
```
[Source](https://github.com/padre-lab-eu/pypads/blob/0cb9f9bd5dff7753f7c47dc691d41edd0426a90a/pypads/base.py#L141)

**Parameters**:
> **uri : string, optional (default=None)** <br> Address of local or remote tracking server that **MLflow** uses to record runs. If None, then it tries to get the environment variable **'MLFLOW_PATH'** or the **'HOMEPATH'** of the user. 
> 
> **name : string, optional (default=None)** <br> Name of the **MLflow** experiment to track.
>
> **mapping_paths : list, optional (default=None)** <br> Absolute paths to additional mapping files.
>
> **mapping : dict, optional (default=None)** <br> Mapping to the logging functions to use for the tracking of the events. If None, then a DEFAULT_MAPPING is used which allow to log parameters, outputs or inputs.
>
> **init_run_fns : list, optional (default=None)** <br> Logging function to execute on tracking initialization.
>
> **include_default_mappings : boolean, optional (default=True)** <br> A flag whether to use the default provided mappings or not.
>
> **logging_fns : dict, optional (default=None)** <br> User defined logging functions to use where each dict item has to be ' "event": fn' or ' "event": {fn1,fn2,...}'.
>
> **config : dict, optional (default=None)** <br> A dictionary that maps the events defined in PyPads mapping files with the logging functions.
>
> **reload_modules : boolean, optional (default=False)** <br> Reload and duck punch already loaded modules before the tracking activation if set to True.
>
> **clear_imports: boolean, optional (default=False)** <br> Delete alredy loaded modules for sys.modules() if set to True.
# Scientific work disclaimer
This was created in scope of scientific work of the Data Science Chair at the University of Passau. If you want to use this tool or any of its resources in your scientific work include a citation.

# Acknowledgement
This work has been partially funded by the **Bavarian Ministry of Economic Affairs, Regional Development and Energy** by means of the funding programm **"Internetkompetenzzentrum Ostbayern"** as well as by the **German Federal Ministry of Education and Research** in the project **"Provenance Analytics"** with grant agreement number *03PSIPT5C*.
