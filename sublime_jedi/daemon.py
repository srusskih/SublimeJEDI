# -*- coding: utf-8 -*-
import os
from os.path import dirname as up, abspath

from functools import wraps
from collections import defaultdict

import jedi

import sublime

from .facade import JediFacade
from .console_logging import getLogger
from .utils import get_settings

logger = getLogger(__name__)

DAEMONS = defaultdict(dict)  # per window


def _get_daemon(view):
    project_path = _find_project(view)
    if project_path not in DAEMONS:
        DAEMONS[project_path] = Daemon(
            project_path=project_path,
            settings=get_settings(view)
        )
    return DAEMONS[project_path]


def _find_project(view):
    directory = up(abspath(view.file_name()))
    while '__init__.py' in os.listdir(directory) and directory != '/':
        directory = up(directory)
    if directory == '/':
        return up(abspath(view.file_name()))
    else:
        return directory


def ask_daemon_sync(view, ask_type, ask_kwargs, location=None):
    """Jedi sync request shortcut.

    :type view: sublime.View
    :type ask_type: str
    :type ask_kwargs: dict or None
    :type location: type of (int, int) or None
    """
    daemon = _get_daemon(view)
    return daemon.request(
        ask_type,
        ask_kwargs or {},
        *_prepare_request_data(view, location)
    )


def ask_daemon(view, callback, ask_type, ask_kwargs=None, location=None):
    """Jedi async request shortcut.

    :type view: sublime.View
    :type callback: callable
    :type ask_type: str
    :type ask_kwargs: dict or None
    :type location: type of (int, int) or None
    """
    window_id = view.window().id()

    def _async_summon():
        answer = ask_daemon_sync(view, ask_type, ask_kwargs, location)
        _run_in_active_view(window_id)(callback)(answer)

    if callback:
        sublime.set_timeout_async(_async_summon, 0)


def _run_in_active_view(window_id):
    """Run function in active ST active view for binded window.

    sublime.View instance would be passed as first parameter to function.
    """
    def _decorator(func):
        @wraps(func)
        def _wrapper(*args, **kwargs):
            for window in sublime.windows():
                if window.id() == window_id:
                    return func(window.active_view(), *args, **kwargs)

            logger.info(
                'Unable to find a window where function must be called.'
            )
        return _wrapper
    return _decorator


def _prepare_request_data(view, location):
    if location is None:
        location = view.sel()[0].begin()
    current_line, current_column = view.rowcol(location)

    filename = view.file_name() or ''
    source = view.substr(sublime.Region(0, view.size()))
    return filename, source, current_line, current_column


class Daemon:
    """Jedi Requester."""

    def __init__(self, project_path, settings):
        """Prepare to call daemon.

        :type settings: dict
        """
        environment_path = (
            settings.get('python_interpreter') or
            settings.get('python_virtualenv') or
            None
        )

        self.project = jedi.Project(
            project_path,
            environment_path=environment_path,
            added_sys_path=settings.get('extra_packages') or [],
        )

        # how to autocomplete arguments
        self.complete_funcargs = settings.get('complete_funcargs')

    def request(
            self,
            request_type,
            request_kwargs,
            filename,
            source,
            line,
            column):
        """Send request to daemon process."""
        logger.info('Sending request to daemon for "{0}"'.format(request_type))
        logger.debug((request_type, request_kwargs, filename, line, column))

        facade = JediFacade(
            project=self.project,
            complete_funcargs=self.complete_funcargs,
            source=source,
            line=line + 1,
            column=column,
            filename=filename,
        )

        answer = facade.get(request_type, request_kwargs)
        logger.debug('Answer: {0}'.format(answer))

        return answer
