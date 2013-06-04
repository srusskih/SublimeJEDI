# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import json
import threading
from collections import namedtuple

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


class BaseThread(threading.Thread, Queue):

    def __init__(self, fd):
        threading.Thread.__init__(self)
        Queue.__init__(self)
        self.fd = fd
        self.daemon = True
        self.done = False
        self.start()


class ThreadReader(BaseThread):

    def run(self):
        while not self.done:
            line = self.fd.readline()
            if line:
                try:
                    data = json.loads(line.strip())
                    self.put(data)
                except ValueError:
                    self.put(line)


class ThreadWriter(BaseThread):

    def run(self):
        while not self.done:
            data = self.get()
            if data:
                if not isinstance(data, str):
                    data = json.dumps(data)
                self.fd.write(data)
                if not data.endswith('\n'):
                    self.fd.write('\n')
                self.fd.flush()


Daemon = namedtuple("Daemon", "process stdin stdout stderr")


def start_daemon(interp, extra_packages, project_name, complete_funcargs):
    sub_kwargs = {'stdin': subprocess.PIPE,
                  'stdout': subprocess.PIPE,
                  'stderr': subprocess.PIPE,
                  'universal_newlines': True,
                  'cwd': CUR_DIR,
                  'bufsize': -1,
                  }
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        sub_kwargs['startupinfo'] = startupinfo
    sub_args = [interp, '-B', 'jedi_daemon.py', '-p', project_name]
    for folder in extra_packages:
        sub_args.extend(['-e', folder])
    sub_args.extend(['-f', complete_funcargs])
    process = subprocess.Popen(sub_args, **sub_kwargs)
    return Daemon(
        process,
        ThreadWriter(process.stdin),
        ThreadReader(process.stdout),
        ThreadReader(process.stderr),
    )
