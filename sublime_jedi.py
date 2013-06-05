# -*- coding: utf-8 -*-
from __future__ import print_function

import os, sys
import functools
from uuid import uuid1
from collections import defaultdict

import sublime
import sublime_plugin

BASE = os.path.abspath(os.path.dirname(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from utils import Empty, start_daemon, is_python_scope

PY3 = sys.version_info[0] == 3
#import pprint
#jedi.set_debug_function(lambda level, *x: pprint.pprint((repr(level), x)))

DAEMONS = defaultdict(dict)  # per window
WAITING = defaultdict(dict)  # per window callback


def get_settings_param(view, param_name, default=None):
    plugin_settings = get_plugin_settings()
    project_settings = view.settings()
    return project_settings.get(
        param_name,
        plugin_settings.get(param_name, default)
    )


def get_plugin_settings():
    setting_name = 'sublime_jedi.sublime-settings'
    plugin_settings = sublime.load_settings(setting_name)
    return plugin_settings


def ask_daemon(view, callback, ask_type, location=None):
    window_id = view.window().id()
    if window_id not in DAEMONS:
        # there is no api to get current project's name
        # so force user to enter it in settings or use first folder in project
        first_folder = ''
        if view.window().folders():
            first_folder = os.path.split(view.window().folders()[0])[-1]
        project_name = get_settings_param(
            view,
            'project_name',
            first_folder,
        )

        daemon = start_daemon(
            interp=get_settings_param(view, 'python_interpreter_path', 'python'),
            extra_packages=get_settings_param(view, 'python_package_paths', []),
            project_name=project_name,
            complete_funcargs=get_settings_param(view, 'auto_complete_function_params', 'all'),
        )

        if not DAEMONS:
            # first time so start loop which will check for gui updates
            sublime.set_timeout(check_sublime_queue, 100)
        DAEMONS[window_id] = daemon

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
        'type': ask_type,
        'uuid': uuid,
    }
    WAITING[window_id][uuid] = {
        'callback': callback,
        'view_id': view.id(),
    }  # XXX track position
    DAEMONS[window_id].stdin.put_nowait(data)


def check_sublime_queue():
    # check for incoming first
    for window_id, daemon in DAEMONS.items():
        for thread in [daemon.stdout, daemon.stderr]:
            try:
                data = thread.get_nowait()
            except Empty:
                continue
            if isinstance(data, dict):
                callback_request = WAITING[window_id].pop(data['uuid'], None)
                if callback_request is None:
                    continue
                for window in sublime.windows():
                    if window.id() == window_id:
                        callback_request['callback'](window.active_view(), data[data['type']])
                        break
            else:
                print(data)

    sublime.set_timeout(check_sublime_queue, 50)


class SublimeJediParamsAutocomplete(sublime_plugin.TextCommand):
    """
    Function / Class constructor autocompletion command
    """
    def run(self, edit, characters='('):
        """
        Insert completion character, and complete function parameters
        if possible

        :param edit: sublime.Edit
        :param characters: str
        """
        self._insert_characters(edit, characters)

        # nothing to do with non-python code
        if not is_python_scope(self.view, self.view.sel()[0].begin()):
            return

        ask_daemon(self.view, self.show_template, 'funcargs', self.view.sel()[0].end())

    def _insert_characters(self, edit, characters):
        """
        Insert autocomplete character with closed pair
        and update selection regions

        :param edit: sublime.Edit
        :param characters: str
        """
        regions = [a for a in self.view.sel()]
        self.view.sel().clear()
        for region in reversed(regions):
            self.view.insert(edit, region.end(), characters + ')')
            position = region.end() + len(characters)
            self.view.sel().add(sublime.Region(position, position))

    def show_template(self, view, template):
        view.run_command('insert_snippet', {"contents": template})


class Autocomplete(sublime_plugin.EventListener):
    """
    Sublime Text autocompletion integration
    """

    completions = []
    cplns_ready = None

    def on_query_completions(self, view, prefix, locations):
        """ Sublime autocomplete event handler

            Get completions depends on current cursor position and return
            them as list of ('possible completion', 'completion type')

            :param view: `sublime.View` object
            :type view: sublime.View
            :param prefix: string for completions
            :type prefix: basestring
            :param locations: offset from beginning
            :type locations: int

            :return: list
        """
        if self.cplns_ready:
            self.cplns_ready = None
            if self.completions:
                cplns, self.completions = self.completions, []
                return [tuple(i) for i in cplns]
            return

        # nothing to do with non-python code
        if not is_python_scope(view, locations[0]):
            return

        # get completions list
        if self.cplns_ready is None:
            ask_daemon(view, self.show_completions, 'autocomplete', locations[0])
            self.cplns_ready = False
        return

    def show_completions(self, view, completions):
        # XXX check position
        self.cplns_ready = True
        if completions:
            self.completions = completions
            view.run_command("hide_auto_complete")
            sublime.set_timeout(functools.partial(self.show, view), 0)

    def show(self, view):
        view.run_command("auto_complete", {
            'disable_auto_insert': True,
            'api_completions_only': True,
            'next_completion_if_showing': False,
            'auto_complete_commit_on_tab': True,
        })
