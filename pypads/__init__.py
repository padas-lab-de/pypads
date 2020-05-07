import sys

from loguru import logger as log
# from .base import PyPads,PypadsApi,PypadsDecorators,PypadsCache
from pypads.parallel import joblib
from pypads.parallel import parallel

logger = log


# import logging
# logger = logging


def set_logger():
    logger.remove()
    logger.add(sys.stdout, filter="pypads", level="INFO")
    logger.add(sys.stderr, filter="pypads", level="INFO")


set_logger()


# __all__ = [
#     'PyPads',
#     'PypadsApi',
#     'PypadsDecorators',
#     'PypadsCache'
# ]