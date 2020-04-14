import sys

from loguru import logger as log

from pypads.parallel import joblib
from pypads.parallel import parallel

logger = log


# import logging
# logger = logging


def set_logger():
    logger.remove()
    logger.add(sys.stdout, format="{time} {level} {name} {message}", filter="my_module", level="INFO")
    # logger.add("error_{time}.log", format="{time} {level} {name} {message}", filter="my_module", level="INFO")


set_logger()
