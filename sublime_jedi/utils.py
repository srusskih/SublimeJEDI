# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import sys
import subprocess
import json
import threading
import warnings
from functools import partial
from collections import defaultdict
from uuid import uuid1
try:
    from Queue import Queue
except ImportError:
    from queue import Queue

import sublime

from .console_logging import getLogger
from .settings import get_settings_param

logger = getLogger(__name__)
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PY3 = sys.version_info[0] == 3
DAEMONS = defaultdict(dict)  # per window


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
                data = None
                try:
                    data = json.loads(line.strip())
                except ValueError:
                    if not isinstance(data, dict):
                        logger.exception(
                            "Non JSON data from daemon: {0}".format(line)
                        )
                else:
                    self.call_callback(data)

    def call_callback(self, data):
        """
        Call callback for response data

        :type data: dict
        """
        if 'logging' in data:
            getattr(logger, data['logging'])(data['content'])
            return

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


class Daemon(object):

    def __init__(self, view):
        window_id = view.window().id()
        self.waiting = dict()
        self.wlock = threading.RLock()
        self.process = self._start_process(get_settings(view))
        self.stdin = ThreadWriter(self.process.stdin, window_id,
                                  self.waiting, self.wlock)
        self.stdout = ThreadReader(self.process.stdout, window_id,
                                   self.waiting, self.wlock)
        self.stderr = ThreadReader(self.process.stderr, window_id,
                                   self.waiting, self.wlock)

    def _start_process(self, settings):
        options = {
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
            options['startupinfo'] = startupinfo

        command = [
            settings['python_interpreter'],
            '-B', 'daemon.py',
            '-p', settings['project_name']
        ]
        for folder in settings['extra_packages']:
            command.extend(['-e', folder])
        command.extend(['-f', settings['complete_funcargs']])

        logger.debug(
            'Daemon process starting with parameters: {0} {1}'
            .format(command, options)
        )
        try:
            return subprocess.Popen(command, **options)
        except OSError:
            logger.error(
                'Daemon process failed with next parameters: {0} {1}'
                .format(command, options)
            )
            raise

    def request(self, view, request_type, callback, location=None):
        """
        Send request to daemon process

        :type view: sublime.View
        :type request_type: str
        :type callback: callabel
        :type location: type of (int, int) or None
        """
        logger.info('Sending request to daemon for "{0}"'.format(request_type))

        if location is None:
            location = view.sel()[0].begin()
        current_line, current_column = view.rowcol(location)
        source = view.substr(sublime.Region(0, view.size()))

        if PY3:
            uuid = uuid1().hex
        else:
            uuid = uuid1().get_hex()

        data = {
            'source': source,
            'line': current_line + 1,
            'offset': current_column,
            'filename': view.file_name() or '',
            'type': request_type,
            'uuid': uuid,
        }
        self.stdin.put_nowait((callback, data))


def ask_daemon(view, callback, ask_type, location=None):
    """
    Daemon request shortcut

    :type view: sublime.View
    :type callback: callabel
    :type ask_type: str
    :type location: type of (int, int) or None
    """
    window_id = view.window().id()

    if window_id not in DAEMONS:
        DAEMONS[window_id] = Daemon(view)

    DAEMONS[window_id].request(view, ask_type, callback, location)


def get_settings(view):
    """
    get settings for daemon

    :type view: sublime.View
    :rtype: dict
    """
    python_interpreter = get_settings_param(view, 'python_interpreter_path')

    if not python_interpreter:
        python_interpreter = get_settings_param(view, 'python_interpreter',
                                                'python')
    else:
        warnings.warn('`python_interpreter_path` parameter is deprecated.'
                      'Please, use `python_interpreter` instead.',
                      DeprecationWarning)

    python_interpreter = expand_project_path(view, python_interpreter)

    extra_packages = get_settings_param(view, 'python_package_paths', [])
    extra_packages = [expand_project_path(view, p) for p in extra_packages]

    complete_funcargs = get_settings_param(view,
                                           'auto_complete_function_params',
                                           'all')

    first_folder = ''
    if view.window().folders():
        first_folder = os.path.split(view.window().folders()[0])[-1]
    project_name = get_settings_param(view, 'project_name', first_folder)

    return {
        'python_interpreter': python_interpreter,
        'extra_packages': extra_packages,
        'project_name': project_name,
        'complete_funcargs': complete_funcargs
    }


def is_python_scope(view, location):
    """ (View, Point) -> bool

    Get if this is a python source scope (not a string and not a comment)
    """
    return view.match_selector(location, "source.python - string - comment")


def to_relative_path(path):
    """
    Trim project root pathes from **path** passed as argument

    If no any folders opened, path will be retuned unchanged
    """
    folders = sublime.active_window().folders()
    for folder in folders:
        # close path with separator
        if folder[-1] != os.path.sep:
            folder += os.path.sep

        if path.startswith(folder):
            return path.replace(folder, '')

    return path


def expand_project_path(view, path):
    """
    expand variable `$project_path` in **path** to project's path

    :type view: sublime.View
    :type path: str
    :rtype: str
    """
    if path.startswith('$project_path'):
        project_dir = os.path.dirname(view.window().project_file_name())
        return path.replace('$project_path', project_dir, 1)
    else:
        return path
