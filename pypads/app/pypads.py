import ast
from typing import Union

import mlflow

from pypads import logger
from pypads.app.base import PyPads, CONFIG_NAME

# Cache configs for runs. Each run could is for now static in it's config.
configs = {}
current_pads = None


# !--- Clean the config cache after run ---


def set_current_pads(pads: Union[None, PyPads]):
    global current_pads
    current_pads = pads


def get_current_pads(init=False) -> Union[None, PyPads]:
    """
    Get the currently active pypads instance. All duck punched objects use this function for interacting with pypads.
    :return:
    """
    global current_pads
    if not current_pads:
        if init:
            # Try to reload pads if it was already defined in the active run
            config = get_current_config()

            if config:
                logger.warning(
                    "PyPads seems to be missing on given run with saved configuration. Reinitializing.")
                return PyPads(config=config)
            else:
                logger.warning(
                    "PyPads has to be initialized before it can be used. Initializing for your with default values.")
                return PyPads()
        else:
            raise Exception(
                "Pypads didn't get initialized and can't be used. Inititalize PyPads by creating an instance.")
    return current_pads


def is_nested_run():
    """
    check whether current run is a nested run.
    :return:
    """
    pads = get_current_pads()
    tags = pads.api.get_run(pads.api.active_run().info.run_id).data.tags
    return "mlflow.parentRunId" in tags


def is_intermediate_run():
    """
    check whether current run is a intermediate run.
    :return:
    """
    pads = get_current_pads()
    return pads.api.is_intermediate_run()


def get_current_config(default=None):
    """
    Get configuration defined in the current mlflow run
    :return:
    """
    global configs
    active_run = mlflow.active_run()
    if active_run in configs.keys():
        return configs[active_run]
    if not active_run:
        return default
    run = mlflow.get_run(active_run.info.run_id)
    if CONFIG_NAME in run.data.tags:
        configs[active_run] = ast.literal_eval(run.data.tags[CONFIG_NAME])
        return configs[active_run]
    return default
