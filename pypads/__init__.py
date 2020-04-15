import sys

from loguru import logger as log

from pypads.parallel import joblib
from pypads.parallel import parallel

logger = log


# import logging
# logger = logging


def set_logger():
    logger.remove()
    logger.add(sys.stdout, filter="pypads", level="INFO")


set_logger()
