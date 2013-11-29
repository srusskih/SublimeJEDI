from __future__ import print_function
import functools
import logging
import traceback
import sublime
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

    def log(self, level, msg, **kwargs):
        """ thread-safe logging """
        log = functools.partial(self._log, level, msg, **kwargs)
        sublime.set_timeout(log, 0)

    def _log(self, level, msg, **kwargs):
        """
        :param level: logging level value
        :param msg: message that logger should prints out
        :param kwargs: dictionary of additional parameters
        """
        if self.level <= level:
            self._print(msg)
            if level == logging.ERROR and kwargs.get('exc_info'):
                traceback.print_exc()

    def debug(self, msg):
        self.log(logging.DEBUG, msg)

    def info(self, msg):
        self.log(logging.INFO, msg)

    def error(self, msg, exc_info=False):
        self.log(logging.ERROR, msg, exc_info=exc_info)

    def exception(self, msg):
        self.error(msg, exc_info=True)


getLogger = Logger
