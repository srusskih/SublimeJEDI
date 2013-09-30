from __future__ import print_function
import logging
import traceback
from .settings import get_plugin_settings


def get_plugin_debug_level():
    default = 'error'
    settings = get_plugin_settings()
    level = settings.get('logging_level', default)
    level = level or default
    return getattr(logging, level.upper())


class Logger:
    """
    Sublime Console Logger that takes plugin settings
    """
    def __init__(self, name):
        self.name = str(name)

    @property
    def level(self):
        return get_plugin_debug_level()

    def _print(self, msg):
        print(': '.join([self.name, str(msg)]))

    def debug(self, msg):
        if self.level <= logging.DEBUG:
            self._print(msg)

    def info(self, msg):
        if self.level <= logging.INFO:
            self._print(msg)

    def error(self, msg, exc_info=False):
        if self.level <= logging.ERROR:
            self._print(msg)
            if exc_info:
                traceback.print_exc()

    def exception(self, msg):
        self.error(msg, exc_info=True)


getLogger = Logger
