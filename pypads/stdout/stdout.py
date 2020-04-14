from loguru import logger

logger.add("error_{time}.log", format="{time} {level} {name} {message}", filter="my_module", level="INFO")
