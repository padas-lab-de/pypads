import io
import os
import sys
import pkg_resources
from typing import List, Type, Union

from pydantic import BaseModel

from pypads import logger
from pypads.app.env import LoggerEnv
from pypads.app.injections.injection import DelayedResultsMixin
from pypads.app.injections.run_loggers import RunSetup, RunTeardown
from pypads.app.injections.tracked_object import TrackedObject
from pypads.model.logger_output import ArtifactMetaModel, TrackedObjectModel, OutputModel
from pypads.model.models import IdReference
from pypads.utils.logging_util import FileFormats
from pypads.importext import pypads_import

original_d_p = pypads_import.duck_punch_loader


def save_imports(spec):
    from pypads.app.pypads import get_current_pads

    pads = get_current_pads()
    if not pads.cache.run_exists("modules"):
        modules = {"pypads", "psutil"}
    else:
        modules = pads.cache.run_get("modules")
    modules.add(spec.name.split(".")[0])
    pads.cache.run_add("modules", modules)

    spec = original_d_p(spec)
    return spec


pypads_import.duck_punch_loader = save_imports


class ContainerizingTO(TrackedObject):

    class ContainerizingModel(TrackedObjectModel):
        type: str = "ContainerizingArtifacts"
        description: str = "Files needed to reproduce the Experiment in an MLproject based on a Dockerfile."

    @classmethod
    def get_model_cls(cls) -> Type[BaseModel]:
        return cls.ContainerizingModel

    def __init__(self, *args, parent: Union[OutputModel, 'TrackedObject'], **kwargs):
        super().__init__(*args, parent=parent, **kwargs)


class IContainerizeRSF(DelayedResultsMixin, RunSetup):

    @staticmethod
    def finalize_output(pads, logger_call, output, *args, **kwargs):
        containerizing = pads.cache.run_get("containerizing")
        is_notebook = pads.cache.run_get("is_notebook")

        def docker(version: str, dependencies: list, commands: list, desc: str):
            """
            Creates the Dockerfile
                Args:
                    version: The Python Version which should be used
                    dependencies: The modules that should be installed
                    commands: A list for additional commands that need to be run when building the Image
                    desc: A short description on how to build the Docker Image
                Returns:
                    The Dockerfile
            """
            f = io.StringIO()
            f.write("FROM python:" + version + "\n\n")
            f.write("RUN mkdir src\n")
            f.write("WORKDIR src/\n")
            f.write("COPY . .\n\n")
            f.write("RUN apt-get update && apt-get install -y git\n")
            f.write("RUN git --version\n")
            f.write("RUN git config --global user.email \"you@example.com\"\n")
            f.write("RUN git config --global user.name \"Your Name\"\n")
            f.write("RUN git init\n\n")
            # TODO: Delete
            f.write("RUN pip install pypads\n")

            for x in dependencies:
                f.write("RUN pip install " + x + "\n")
            for x in commands:
                f.write("RUN " + x + "\n")
            f.write("\n# " + desc)
            dockerfile = f.getvalue()
            f.close()
            return dockerfile

        def mlpr(entry: str, parameters: list, desc: str):
            """
            Creates the MLproject File
                Args:
                    entry: The name of the Python script that acts as an entry point
                    parameters: A list of parameters and their default values for the script
                    desc: A short description on how to run the MLproject
                Returns:
                    The MLproject File
            """
            f = io.StringIO()
            f.write("name: " + entry + "-run\n\n")
            f.write("docker_env:\n")
            f.write("  image:  " + entry + "-base\n\n")
            f.write("entry_points:\n")
            f.write("  main:\n")
            # check if there are any parameters and if so, add them to the MLproject file
            pars = ""  # string that holds the parameter names to append them to the entry point command
            if len(parameters) is not 0:
                f.write("    parameters:\n")
                for x in parameters:
                    par, value = x
                    f.write("      " + par + ": {default: " + value + "}\n")
                    pars += " " + par + " {" + par + "}"
            # the entry point command. Changes depending on whether the experiment is a script or notebook
            if is_notebook:
                f.write("    command: \"jupyter notebook --port=8888 --no-browser --ip=0.0.0.0 --allow-root\"\n")
            else:
                f.write("    command: \"python " + entry + ".py" + pars + "\"\n")

            f.write("\n# " + desc)
            mlproject = f.getvalue()
            f.close()
            return mlproject

        def does_module_exist(module):
            """
            Checks if a given module exists in PyPI.
            """
            import requests
            response = requests.get("https://pypi.python.org/pypi/" + module)
            if response.status_code is 200:
                return True

        def get_module_names(modules_imp: set):
            """
            This is a modified Version of the "get_pkg_names" function from pipreqs.
            https://github.com/bndr/pipreqs/blob/master/pipreqs/pipreqs.py

            Get PyPI package names from a list of imports.
                Args:
                    modules_imp (List[str]): List of import names.
                Returns:
                    List[str]: The corresponding PyPI package names.
            """
            modules_pypi = set()
            missing_modules = set()
            mapping = pkg_resources.resource_filename('pypads', 'bindings/resources/dependencies/PyPI-mapping')
            # open the mapping file and create a dictionary from its entries
            with open(mapping, "r") as f:
                names = dict(x.strip().split(":") for x in f)
            for module in modules_imp.copy():
                module_pypi = names.get(module, module).replace("-", "_")
                if does_module_exist(module_pypi):
                    modules_pypi.add(module_pypi)
                else:
                    missing_modules.add(module_pypi)
            #                if module in names:
            #                    modules_pypi.add(names.get(module).replace("-", "_"))
            #                else:
            #                    missing_modules.add(module)
            if len(missing_modules) is not 0:
                logger.warning("Following imported Modules could not be found at PyPI: " + ", ".join(missing_modules) +
                               ". You might want to add them via the '_additional_modules' parameter if they are "
                               "crucial for your experiment.")
            return modules_pypi

        def get_module_versions(module_names: set):
            """
            Takes the list of PyPI package names and adds the corresponding version numbers.
                Args:
                    module_names: Set of PyPI names
                Returns:
                    List[str]: The corresponding Version numbers that are installed on the system.
            """
            module_versions = list()

            # add jupyter to the set of modules if the experiment is run in a notebook
            if is_notebook:
                module_names.add("jupyter")

            # import pip freeze
            try:
                # noinspection PyProtectedMember,PyPackageRequirements
                from pip._internal.operations import freeze
            except ImportError:  # pip < 10.0
                # noinspection PyUnresolvedReferences,PyPackageRequirements
                from pip.operations import freeze
            # run pip freeze and check if its entries appear in the modules list, if so add them to the results list
            # along with the corresponding version number
            # since PyPI doesnt differentiate between '-' and '_' so the latter is used by default
            for item in list(freeze.freeze()):
                if "==" in item:
                    name, version = item.split("==")
                    if name.replace("-", "_") in module_names:
                        module_versions.append(item)
            logger.info("Following Packages have been tracked: " + ", ".join(module_versions))
            return module_versions

        # check for modules in cache and convert them to the right format
        if pads.cache.run_exists("modules"):
            modules = get_module_versions(get_module_names(pads.cache.run_get("modules")))
        else:
            modules = list()
        modules.extend(pads.cache.run_get("extra-modules"))

        name = pads.cache.run_get("name").split(".")[0]

        memory = list(pads.results.get_tracked_objects(run_id=pads.api.active_run().info.run_id,
                                                       type="RamInformation"))[0].total_memory
        o_system = list(pads.results.get_tracked_objects(run_id=pads.api.active_run().info.run_id,
                                                       type="SystemInformation"))[0].system
        min_freq = list(pads.results.get_tracked_objects(run_id=pads.api.active_run().info.run_id,
                                                         type="CpuInformation"))[0].min_freq
        max_freq = list(pads.results.get_tracked_objects(run_id=pads.api.active_run().info.run_id,
                                                         type="CpuInformation"))[0].max_freq
        t_cores = list(pads.results.get_tracked_objects(run_id=pads.api.active_run().info.run_id,
                                                            type="CpuInformation"))[0].total_cores
        p_cores = list(pads.results.get_tracked_objects(run_id=pads.api.active_run().info.run_id,
                                                               type="CpuInformation"))[0].physical_cores

        system = "# The Experiment has originally been run on a system with the following specifications:\n# OS: " + \
                 o_system + "\n# RAM: " + memory + "\n# Physical cores: " + str(p_cores) + "\n# Total cores: " + \
                 str(t_cores) + "\n# Minimal frequency: " + min_freq + "\n# Maximal frequency: " + max_freq

        # meta entries for Dockerfile and MLproject
        desc_dock = "This Dockerfile was generated by the IContainerize function and it contains the environment " \
                    "needed to run your experiment. Use 'docker build -t " + name + "-base .' to build it.\n\n" + system
        if is_notebook:
            mlrun = "'mlflow run --docker-args publish=8888:8888 .'"
        else:
            mlrun = "'mlflow run .'"
        desc_mlpr = "This MLproject was generated by the IContainerize function and it can be used to run your " \
                    "experiment. After building the Docker Image using the Dockerfile that was generated as well, " \
                    "you can run it using " + mlrun + "\n\n" + system

        # generate MLproject and Dockerfile and save them as artifacts
        pads.api.log_mem_artifact(path="Dockerfile", write_format=FileFormats.unknown, description=desc_dock,
                                  obj=docker(pads.cache.run_get("ver"), modules, pads.cache.run_get("commands"),
                                             desc_dock))

        pads.api.log_mem_artifact(path="MLproject", obj=mlpr(name, pads.cache.run_get("params"), desc_mlpr),
                                  write_format=FileFormats.unknown, description=desc_mlpr)

        # create a file that contians the runs environment variables
        def envfile(desc):
            env_vars = dict(os.environ)
            f = io.StringIO()
            f.write("# " + desc + "\n\n")
            for k in env_vars:
                f.write(k + "=" + env_vars[k] + "\n")

            env_file = f.getvalue()
            return env_file

        desc_env = "This file was generated by the IContainerize function. It contains your system's environment " \
                   "variables. Place this in the same folder as your Dockerfile to automatically include the " \
                   "variables in your Docker Image."

        pads.api.log_mem_artifact(path=".env", obj=envfile(desc_env), write_format=FileFormats.unknown,
                                  description=desc_env)

        # save notebook execution as artifact
        if is_notebook:
            from IPython import get_ipython

            desc_note = "This Notebook was generated by the IContainerize function and it mirrors the execution of " \
                        "the tracked Notebook. Place this in the same folder as the Dockerfile and MLproject."
            get_ipython().run_line_magic("notebook", "notebook_execution.ipynb")

            pads.api.log_artifact(local_path="notebook_execution.ipynb", description=desc_note,
                                  artifact_path="notebook_execution.ipynb")

        output.ContainerizingTO = containerizing.store()

    name = "Containerizing Run Setup Logger"
    type: str = "ContainerizingRunLogger"

    class IContainerizeRSFOutput(OutputModel):
        type: str = "IContainerizeRSF-Output"
        logs: IdReference = ...

    @classmethod
    def output_schema_class(cls) -> Type[OutputModel]:
        return cls.IContainerizeRSFOutput

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _call(self, *args, _pypads_env: LoggerEnv, _logger_call, _logger_output, **kwargs):
        pads = _pypads_env.pypads
        if not pads.cache.run_exists("containerizing"):
            containerizing = ContainerizingTO(parent=_logger_output)
            pads.cache.run_add("containerizing", containerizing)

            _additional_modules = kwargs.get("_additional_modules") if kwargs.get("_additional_modules") else set()
            _additional_commands = kwargs.get("_additional_commands") if kwargs.get("_additional_commands") else set()

            # add the additional dependencies to the cache
            pads.cache.run_add("extra-modules", _additional_modules)
            pads.cache.run_add("commands", _additional_commands)

            # get version number and add it to the cache in format in the desired format
            ver = sys.version_info
            pads.cache.run_add("ver", str(ver.major) + "." + str(ver.minor))

            name = os.path.split(sys.argv[0])[1]

            if name != "ipykernel_launcher.py":
                # get script name and add it to the cache
                pads.cache.run_add("name", name)
                pads.cache.run_add("is_notebook", False)

                # get input parameters and add add a list with Key-Value-pairs to the cache
                params = list()
                if len(sys.argv) > 1 and len(sys.argv) % 2 is 1:
                    for x in range(len(sys.argv)):
                        if x % 2 is 1:
                            params.append([sys.argv[x], sys.argv[x + 1]])
                pads.cache.run_add("params", params)
            else:
                pads.cache.run_add("name", "notebook")
                pads.cache.run_add("is_notebook", True)
                params = list()
                pads.cache.run_add("params", params)

        else:
            logger.warning("IContainerizeRSF already registered")