# -*- coding: utf-8 -*-

import os
import functools
from uuid import uuid1
from collections import defaultdict

import sublime
import sublime_plugin

try:
    from SublimeJEDI.utils import Empty, get_settings_param, start_daemon
except ImportError:
    from utils import Empty, get_settings_param, start_daemon

#import pprint
#jedi.set_debug_function(lambda level, *x: pprint.pprint((repr(level), x)))

DAEMONS = defaultdict(dict)  # per window
WAITING = defaultdict(dict)  # per window callback


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
                print data

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
        # nothing to do with non-python code
        if 'python' not in view.settings().get('syntax').lower():
            return

        if 'python string' in view.scope_name(locations[0]):
            return

        if self.completions:
            cplns, self.completions = self.completions, []
            return [tuple(i) for i in cplns]

        # get completions list
        ask_daemon(view, self.show_completions, 'autocomplete', locations[0])
        return

    def show_completions(self, view, completions):
        # XXX check position
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
