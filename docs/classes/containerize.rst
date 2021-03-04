.. _containerize:

Containerize
============
If you use this Logger, it tracks your Python Modules as they are being imported and saves a *MLproject* and
*Dockerfile* to your run artifacts that can be used to reproduce your experiment.

Features:
-----------
The function tracks the following artifacts needed to run your Experiment:

- Python version
- Python packages
- Input parameters
- Evnironment variables

It works for basic Python scripts as well as Jupyter Notebooks that use a Python kernel.

How to use:
-----------
Place the *MLproject* and *Dockerfile* along with your Python script and other files you need in a folder and run
``"docker build -t [Name of your script]-base ."`` (This command will also be provided to you inside the Dockerfile as a
comment) to build the base Docker image and then use ``"mlflow run ."`` to start your MLflow Run.

When using a *Jupyter Notebook*, the port-address needs to be forwarded from inside the *Docker* Container. To do so, use
``"mlflow run --docker-args publish=8888:8888 ."`` when running the *MLflow* project. This command will again be
provided to you in the corresponding *MLproject* file.

Troubleshooting:
----------------
If for some reason some of your dependencies dont get recognized, you can call the logger with the parameter
"_additional_modules" to provide a list with the missing dependencies.
If any additional commands need to get executed when building the Docker Image (for examlpe installing a setup.py-file)
you can use the "_additional_commands" parameter to provide a list of commands.

Please keep in mind, that the Logger tracks all environment variables and stores them in a .env-file, which you should
include in your Docker Image if needed. You can edit the file to delete certain variables that you dont intend to share.