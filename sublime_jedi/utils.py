# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import json
import re
from functools import partial, wraps
from collections import defaultdict

import jedi
from jedi.api import environment

import sublime

from .daemon import JediFacade
from .console_logging import getLogger
from .settings import get_settings_param

logger = getLogger(__name__)
DAEMONS = defaultdict(dict)  # per window


def ask_daemon(view, callback, ask_type, location=None):
    """Daemon request shortcut.

    :type view: sublime.View
    :type callback: callable
    :type ask_type: str
    :type location: type of (int, int) or None
    """
    window_id = view.window().id()
    window_callback = run_in_active_view(window_id)(callback)

    if window_id not in DAEMONS:
        DAEMONS[window_id] = Daemon(settings=get_settings(view))

    if location is None:
        location = view.sel()[0].begin()
    current_line, current_column = view.rowcol(location)

    filename = view.file_name() or ''
    # do not pass file content, if file saved
    source = view.substr(sublime.Region(0, view.size()))

    def _summon_daemon():
        answer = DAEMONS[window_id].request(
            ask_type,
            filename,
            source,
            current_line,
            current_column
        )
        sublime.set_timeout(partial(window_callback, answer), 0)

    sublime.set_timeout_async(_summon_daemon, 0)


class Daemon(object):

    def __init__(self, settings):
        """Prepare to call daemon.

        :type settings: dict
        """
        python_virtualenv = settings.get('python_virtualenv')
        python_interpreter = settings.get('python_interpreter')

        logger.debug('Jedi Environment: {0}'.format(
            (python_virtualenv, python_interpreter))
        )

        if python_virtualenv:
            self.env = environment.create_environment(python_virtualenv,
                                                      safe=False)
        elif python_interpreter:
            self.env = environment.Environment(
                environment._get_python_prefix(python_interpreter),
                python_interpreter
            )
        else:
            self.env = jedi.get_default_environment()

        self.sys_path = self.env.get_sys_path()
        # prepare the extra packages if any
        extra_packages = settings.get('extra_packages')
        if extra_packages:
            self.sys_path = extra_packages + self.sys_path

        # how to autocomplete arguments
        self.complete_funcargs = settings.get('complete_funcargs')
        self.follow_imports = settings.get('follow_imports')

    def request(self, request_type, filename, source, line, column):
        """Send request to daemon process."""
        logger.info('Sending request to daemon for "{0}"'.format(request_type))
        logger.debug((request_type, filename, source, line, column))

        facade = JediFacade(
            env=self.env,
            complete_funcargs=self.complete_funcargs,
            source=source,
            line=line + 1,
            column=column,
            filename=filename,
            sys_path=self.sys_path,
            follow_imports=self.follow_imports
        )

        answer = facade.get(request_type)
        logger.debug('Answer: {0}'.format(answer))
        return answer


def run_in_active_view(window_id):
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


def get_settings(view):
    """Get plugin settings.

    :type view: sublime.View
    :rtype: dict
    """
    python_virtualenv = get_settings_param(view, 'python_virtualenv', None)
    if python_virtualenv:
        python_virtualenv = expand_path(view, python_virtualenv)

    python_interpreter = get_settings_param(view, 'python_interpreter', None)
    if python_interpreter:
        python_interpreter = expand_path(view, python_interpreter)

    extra_packages = get_settings_param(view, 'python_package_paths', [])
    extra_packages = [expand_path(view, p) for p in extra_packages]

    complete_funcargs = get_settings_param(
        view, 'auto_complete_function_params', 'all')

    enable_in_sublime_repl = get_settings_param(
        view, 'enable_in_sublime_repl', False)

    follow_imports = get_settings_param(view, 'follow_imports', True)

    first_folder = ''
    if view.window().folders():
        first_folder = os.path.split(view.window().folders()[0])[-1]
    project_name = get_settings_param(view, 'project_name', first_folder)

    return {
        'python_interpreter': python_interpreter,
        'python_virtualenv': python_virtualenv,
        'extra_packages': extra_packages,
        'project_name': project_name,
        'complete_funcargs': complete_funcargs,
        'enable_in_sublime_repl': enable_in_sublime_repl,
        'follow_imports': follow_imports,
    }


def is_python_scope(view, location):
    """ (View, Point) -> bool

    Get if this is a python source scope (not a string and not a comment)
    """
    return view.match_selector(location, "source.python - string - comment")


class PythonCommandMixin(object):
    """A mixin that hides and disables command for non-python code """

    def is_visible(self):
        """ The command is visible only for python code """
        return is_python_scope(self.view, self.view.sel()[0].begin())

    def is_enabled(self):
        """ The command is enabled only when it is visible """
        return self.is_visible()


def is_repl(view):
    """Check if a view is a REPL."""
    return view.settings().get("repl", False)


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


def split_path(d, keys):
    assert isinstance(d, dict) and isinstance(keys, list)
    for k in [x for x in keys if d.get(x) and os.path.exists(d[x])]:
        d['%s_path' % k], d['%s_name' % k] = os.path.split(d[k])
        d['%s_base_name' % k], d['%s_extension' % k] = \
            os.path.splitext(d['%s_name' % k])
        d['%s_extension' % k] = d['%s_extension' % k].lstrip('.')
    return d


def expand_path(view, path):
    """
    Expand ST build system and OS environment variables to normalized path
    that allows collapsing up-level references for basic path manipulation
    through combination of variables and/or separators, i.e.:
        "python_interpreter": "$project_path/../../virtual/bin/python",
        "python_package_paths": ["$home/.buildout/eggs"]

    :type view: sublime.View
    :type path: str
    :rtype: str
    """
    subl_vars = {}
    try:
        subl_vars['$file'] = view.file_name()
        subl_vars['$packages'] = sublime.packages_path()

        try:
            subl_vars['$project'] = view.window().project_file_name()
        except AttributeError:
            subl_vars['$project'] = get_project_file_name(view.window())

        subl_vars = split_path(subl_vars, ['$file', '$project'])
        if '$' in path or '%' in path:
            exp_path = path
            for k in sorted(subl_vars, key=len, reverse=True):
                if subl_vars[k]:
                    exp_path = exp_path.replace(k, subl_vars[k])
            exp_path = os.path.normpath(os.path.expandvars(exp_path))
            if os.path.exists(exp_path):
                path = exp_path
    except Exception:
        logger.exception('Exception while expanding "{0}"'.format(path))

    return path


def get_project_file_name(window):
    """Getting project file name for ST2."""
    if not window.folders():
        return None

    projects = _get_projects_from_session()

    for project_file in projects:
        project_file = re.sub(r'^/([^/])/', '\\1:/', project_file)
        project_json = json.loads(file(project_file, 'r').read(), strict=False)

        if 'folders' in project_json:
            folders = project_json['folders']
            found_all = True
            for directory in window.folders():
                found = False
                for folder in folders:
                    folder_path = re.sub(r'^/([^/])/', '\\1:/', folder['path'])
                    if folder_path == directory.replace('\\', '/'):
                        found = True
                        break
                if not found:
                    found_all = False
                    break

        if found_all:
            return project_file
    return None


def _get_projects_from_session():
    session_file_path = os.path.join(sublime.packages_path(), '..', 'Settings', 'Session.sublime_session')
    auto_session_file_path = os.path.join(sublime.packages_path(), '..', 'Settings', 'Auto Save Session.sublime_session')

    projects = []

    for file_path in [session_file_path, auto_session_file_path]:
        try:
            with file(os.path.normpath(file_path), 'r') as fd:
                data = fd.read().replace('\t', ' ')
                data = json.loads(data, strict=False)
                projects += data.get('workspaces', {}).get('recent_workspaces', [])
        except:
            logger.info("File {0} missed".format(file_path))
            continue

    projects = list(set(projects))

    return projects


def is_sublime_v2():
    return sublime.version().startswith('2')
