# pypads
Building on the MLFlow toolset this project aims to extend the functionality for MLFlow, increase the automation and therefore reduce the workload for the user. The production of structured results is an additional goal of the extension.

# Concept
Logging results of machine learning workflows often shares similar structures and goals. You might want to track parameteres, loss functions, metrics or other characteristic numbers. While the produced output shares a lot of concepts and could be standardized, implementations are diverse and integrating them or their autologging functionality into such a standard needs manual labour. Each and every version of a library might change internal structures and hard coding interfaces can need intesive work. Pypads aims to feature following main techniques to handle autologging and standardization efforts:
- **Community driven mapping files:** A means to log data from python libaries like sklearn. Interfaces are not added directly to MLFlows, but derived from versioned mapping files of frameworks.
- **Output standardization:** TODO
- **Dataset management:** TODO


# Scientific work disclaimer
If you want to use this tool or any of its resources in your scientific work include a citation.
