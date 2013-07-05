# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import sys
import subprocess
import json
import threading
from functools import partial
from collections import namedtuple

try:
    from Queue import Queue
    from console_logging import getLogger
except ImportError:
    from queue import Queue
    from .console_logging import getLogger

logger = getLogger(__name__)
CUR_DIR = os.path.dirname(os.path.abspath(__file__))

import sublime


def run_in_active_view(window_id, callback, response):
    for window in sublime.windows():
        if window.id() == window_id:
            callback(window.active_view(), response)
            break


class BaseThread(threading.Thread):

    def __init__(self, fd, window_id, waiting, lock):
        self.fd = fd
        self.done = False
        self.waiting = waiting
        self.wait_lock = lock
        self.window_id = window_id
        super(BaseThread, self).__init__()
        self.daemon = True
        self.start()


class ThreadReader(BaseThread):

    def run(self):
        while not self.done:
            line = self.fd.readline()
            if line:
                try:
                    data = json.loads(line.strip())
                except ValueError:
                    self.call_callback(line)
                else:
                    self.call_callback(data)

    def call_callback(self, data):
        if not isinstance(data, dict):
            logger.exception(
                "JEDI: Non JSON data from daemon: {}"
                .format(data)
            )

        with self.wait_lock:
            callback = self.waiting.pop(data['uuid'], None)

        if callback is not None:
            delayed_callback = partial(
                run_in_active_view,
                self.window_id,
                callback,
                data[data['type']]
            )
            sublime.set_timeout(delayed_callback, 0)


class ThreadWriter(BaseThread, Queue):

    def __init__(self, *args, **kwargs):
        Queue.__init__(self)
        super(ThreadWriter, self).__init__(*args, **kwargs)

    def run(self):
        while not self.done:
            request_data = self.get()

            if not request_data:
                continue

            callback, data = request_data

            with self.wait_lock:
                self.waiting[data['uuid']] = callback

            if not isinstance(data, str):
                data = json.dumps(data)

            self.fd.write(data)
            if not data.endswith('\n'):
                self.fd.write('\n')
            self.fd.flush()


Daemon = namedtuple("Daemon", "process stdin stdout stderr")


def start_daemon(window_id, interp, extra_packages, project_name, complete_funcargs):
    sub_kwargs = {
        'stdin': subprocess.PIPE,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'universal_newlines': True,
        'cwd': CUR_DIR,
        'bufsize': -1,
    }

    # hide "cmd" window in Windows
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        sub_kwargs['startupinfo'] = startupinfo

    sub_args = [interp, '-B', 'jedi_daemon.py', '-p', project_name]
    for folder in extra_packages:
        sub_args.extend(['-e', folder])
    sub_args.extend(['-f', complete_funcargs])
    process = subprocess.Popen(sub_args, **sub_kwargs)
    waiting = dict()
    wlock = threading.RLock()
    return Daemon(
        process,
        ThreadWriter(process.stdin, window_id, waiting, wlock),
        ThreadReader(process.stdout, window_id, waiting, wlock),
        ThreadReader(process.stderr, window_id, waiting, wlock),
    )


def is_python_scope(view, location):
    """ (View, Point) -> bool

    Get if this is a python source scope (not a string and not a comment)
    """
    return view.match_selector(location, "source.python - string - comment")
