# pypads
Building on the MLFlow toolset this project aims to extend the functionality for MLFlow, increase the automation and therefore reduce the workload for the user. The production of structured results is an additional goal of the extension.

# Concept
Logging results of machine learning workflows often shares similar structures and goals. You might want to track parameteres, loss functions, metrics or other characteristic numbers. While the produced output shares a lot of concepts and could be standardized, implementations are diverse and integrating them or their autologging functionality into such a standard needs manual labour. Each and every version of a library might change internal structures and hard coding interfaces can need intesive work. Pypads aims to feature following main techniques to handle autologging and standardization efforts:
- **Automatic metric tracking:** TODO
- **Automatic execution tracking:** TODO 
- **Community driven mapping files:** A means to log data from python libaries like sklearn. Interfaces are not added directly to MLFlows, but derived from versioned mapping files of frameworks.
- **Output standardization:** TODO
- **Dataset management:** TODO

# Getting started
This tool requires those libraries to work:

        mlflow>=1.4.0
        pytest>=5.2.4
        boltons>=19.3.0
To install pypads from source, clone the source code repository and run
   
        python setup.py install
        
### Usage
pypads is easy to use. Just define what is needed to be tracked in the config and call PyPads.

        from pypads.base import PyPads
        # define the configuration, in this case we want to track the parameters, 
        # outputs and the inputs of each called function included in the hooks (pypads_fit, pypads_predict)
        config = {'events': {
                    "parameters" : ['pypads_fit'],
                    "outputs" : ['pypads_predict', 'pypads_fit'],
                    "inputs" : ['pypads_fit']
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
        
The used hooks for each event are defined in the mapping json file and each hook should include the functions to track on call.
In the example of sklearn mapping json file, we have:

        "hook_fns": {
            "pypads_fit": [
                "fit", "fit_predict", "fit_transform"
            ],
            "pypads_predict": [
                "fit_predict", "predict", "score"
            ],
            "pypads_transform": [
                "fit_transform", "transform"
            ]
        }
        
# Scientific work disclaimer
If you want to use this tool or any of its resources in your scientific work include a citation.
