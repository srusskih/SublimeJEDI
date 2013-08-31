import sys
import logging


def getLogger(name, level=None):
    logger = logging.getLogger(name)

    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)

    logger.setLevel(level or logging.ERROR)

    return logger
