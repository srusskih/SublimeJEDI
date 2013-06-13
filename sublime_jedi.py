# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import functools
from uuid import uuid1
from collections import defaultdict

import sublime
import sublime_plugin

BASE = os.path.abspath(os.path.dirname(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from utils import start_daemon, is_python_scope

PY3 = sys.version_info[0] == 3
#import pprint
#jedi.set_debug_function(lambda level, *x: pprint.pprint((repr(level), x)))

DAEMONS = defaultdict(dict)  # per window


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

    # check if thread needs a restart
    daemon = DAEMONS.get(window_id)
    if daemon is not None and daemon.stdin.restart_needed is not False:
        print('daemon process has died with "%s"' % daemon.stdin.restart_needed)
        DAEMONS.pop(window_id)
        daemon.process.terminate()
        daemon = None

    if daemon is None:
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
            window_id=window_id,
            interp=get_settings_param(view, 'python_interpreter_path', 'python'),
            extra_packages=get_settings_param(view, 'python_package_paths', []),
            project_name=project_name,
            complete_funcargs=get_settings_param(view, 'auto_complete_function_params', 'all'),
        )

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
    daemon.stdin.put_nowait((callback, data))


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
