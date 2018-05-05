import logging
import os
import sys

# add dependencies on package initialization
sys.path.append(os.path.join(os.path.dirname(__file__), 'dependencies'))

try:
    from .sublime_jedi import *
except ImportError:
    logging.exception("Error during importing .sublime_jedi package")
    raise
