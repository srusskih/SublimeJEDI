# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import functools
import itertools
import sys
import subprocess
import socket
import time
import json
import threading
from functools import partial

try:
    from console_logging import getLogger
except ImportError:
    from .console_logging import getLogger

logger = getLogger(__name__)
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_ID = 2 ** 32
CLEAN_UPS = list()

sys.path.insert(0, CUR_DIR)
from typhoon import ioloop, iostream
sys.path.pop(0)

import sublime


class JediTCPClient(object):

    def __init__(self, window_id, host='127.0.0.1', port=8888):
        self.window_id = window_id
        self.host = host
        self.port = port
        self.id_gen = itertools.count(1)
        self.waiters = dict()
        self.stream = None

    def start(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.stream = iostream.IOStream(s)
        self.stream.connect((self.host, self.port), self.on_connection)

    def on_connection(self):
        pass

    def send_request(self, callback, data):
        data['uuid'] = next(self.id_gen) % MAX_ID
        self.waiters[data['uuid']] = callback
        data = json.dumps(data)
        self.stream.write(data.encode('utf-8'))
        self.stream.write(b'\n')
        self.stream.read_until(b'\n', self.on_data)

    def on_data(self, line):
        data = json.loads(line.decode('utf-8').strip())
        callback = self.waiters.pop(data['uuid'], None)

        if callback is not None:
            delayed_callback = partial(
                run_in_active_view,
                self.window_id,
                callback,
                data[data['type']]
            )
            sublime.set_timeout(delayed_callback, 0)


def run_in_active_view(window_id, callback, response):
    # debug, window_id is 0 at start
    callback(sublime.active_window().active_view(), response)
    return

    for window in sublime.windows():
        if window.id() == window_id:
            callback(window.active_view(), response)
            break


def start_daemon(interp, extra_packages, project_name, complete_funcargs):
    log_file = os.path.join(CUR_DIR, 'server-%s.txt' % int(time.time()))
    stdout = open(log_file, 'a')
    CLEAN_UPS.append(functools.partial(stdout.write, 'at end\n'))
    CLEAN_UPS.append(functools.partial(stdout.close))
    sub_kwargs = dict(cwd=CUR_DIR, stdout=stdout, stderr=subprocess.STDOUT)

    # hide "cmd" window in Windows
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        sub_kwargs['startupinfo'] = startupinfo

    sub_args = [interp, '-B', 'jedi_daemon.py', '-p', project_name,
                '--port', '8882']
    for folder in extra_packages:
        sub_args.extend(['-e', folder])
    sub_args.extend(['-f', complete_funcargs])
    process = subprocess.Popen(sub_args, **sub_kwargs)
    CLEAN_UPS.append(functools.partial(process.terminate))
    return process

daemon_proc = start_daemon('python', list(), 'unknown', 'all')


def start_client(io_loop, tcp_client):
    io_loop.make_current()
    tcp_client.start()
    io_loop.start()

io_loop = None
tcp_client = None


def send_request(callback, data):
    io_loop.add_callback(tcp_client.send_request, callback, data)


def is_python_scope(view, location):
    """ (View, Point) -> bool

    Get if this is a python source scope (not a string and not a comment)
    """
    return view.match_selector(location, "source.python - string - comment")


def plugin_loaded():
    # ST3 has some strange import logic, it runs module code multiple
    # times, so we have to workaround with global variables.
    global io_loop
    global tcp_client
    io_loop = ioloop.IOLoop()
    tcp_client = JediTCPClient(0, port=8882)
    _t = threading.Thread(target=start_client, args=(io_loop, tcp_client))
    _t.start()
    CLEAN_UPS.append(functools.partial(io_loop.add_callback, io_loop.stop))


def plugin_unloaded():
    for cb in CLEAN_UPS:
        try:
            cb()
        except Exception:
            pass
