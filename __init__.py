# fix absolute imports on ST3
# TODO: remove
#import sys
#import os
#sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from sublime_jedi import *
except ImportError:
    from .sublime_jedi import *
