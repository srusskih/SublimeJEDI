# -*- coding: utf-8 -*-
import os
import json
import sys
import copy
import subprocess
from collections import defaultdict
from contextlib import contextmanager

import sublime
import sublime_plugin

BASE = os.path.abspath(os.path.dirname(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import jedi

#import pprint
#jedi.set_debug_function(lambda level, *x: pprint.pprint((repr(level), x)))

_dotcomplete = []


def get_script(view, location):
    """ `jedi.Script` fabric

        :param view: `sublime.View` object
        :type view: sublime.View
        :param location: offset from beginning
        :type location: int

        :return: `jedi.api.Script` object
    """
    text = view.substr(sublime.Region(0, view.size()))
    source_path = view.file_name()
    current_line, current_column = view.rowcol(location)
    script = jedi.Script(
        text,
        current_line + 1,
        current_column,
        source_path or ''  # if 'untitled' tab then file_name will be `None`
    )
    return script


def get_plugin_settings():
    setting_name = 'sublime_jedi.sublime-settings'
    plugin_settings = sublime.load_settings(setting_name)
    return plugin_settings


class JediEnvMixin(object):
    """ Mixin to install user virtual env for JEDI """

    SYS_ENVS = defaultdict(dict)  # key = window.id value = dict interpeter path : sys.path
    SETTINGS_INTERP = 'python_interpreter_path'
    _origin_env = copy.copy(sys.path)

    def get_sys_path(self, python_interpreter):
        """ Get PYTHONPATH for passed interpreter and return it

            :param python_interpreter: python interpreter path
            :type python_interpreter: unicode or buffer

            :return: list
        """
        command = [python_interpreter, '-c', "import sys; print(sys.path)"]
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.Popen(command, shell=False,
                                       stdout=subprocess.PIPE,
                                       startupinfo=startupinfo)
        else:
            process = subprocess.Popen(command, shell=False,
                                       stdout=subprocess.PIPE)
        out = process.communicate()[0].decode('utf-8')
        sys_path = json.loads(out.replace("'", '"'))
        return sys_path

    def reset_sys_envs(self, window_id):
        self.SYS_ENVS[window_id].clear()

    def get_user_env(self):
        """ Gets user's interpreter from the settings and returns
            PYTHONPATH for this interpreter

            :return: list
        """
        # load settings
        plugin_settings = get_plugin_settings()
        project_settings = sublime.active_window().active_view().settings()

        # get user interpreter, or get system default
        interpreter_path = project_settings.get(
            self.SETTINGS_INTERP,
            plugin_settings.get(self.SETTINGS_INTERP)
        )
        window_id = sublime.active_window().id()

        if interpreter_path not in self.SYS_ENVS[window_id]:
            # register callback which will drop cached sys.path
            plugin_settings.add_on_change(
                self.SETTINGS_INTERP,
                lambda: self.reset_sys_envs(window_id)
            )
            project_settings.add_on_change(
                self.SETTINGS_INTERP,
                lambda: self.reset_sys_envs(window_id)
            )

            sys_path = self.get_sys_path(interpreter_path)

            # get user interpreter, or get system default
            package_paths = project_settings.get(
                'python_package_paths',
                plugin_settings.get('python_package_paths')
            )

            # extra paths should in the head on the sys.path list
            # to override "default" packages from in the environment
            sys_path = package_paths + sys_path
            self.SYS_ENVS[window_id][interpreter_path] = sys_path
        return self.SYS_ENVS[window_id][interpreter_path]

    @property
    @contextmanager
    def env(self):
        env = self.get_user_env()
        sys.path = copy.copy(env)
        try:
            yield
        finally:
            sys.path = copy.copy(self._origin_env)


class SublimeMixin(object):
    """ helpers to integrate sublime """

    def is_funcargs_complete_enabled(self, view):
        plugin_settings = get_plugin_settings()
        project_settings = view.settings()
        return project_settings.get(
            'auto_complete_function_params',
            plugin_settings.get('auto_complete_function_params', True)
        )

    def format(self, complete, insert_funcargs=True):
        """ Returns a tuple of the string that would be visible in the completion
            dialogue, and the snippet to insert for the completion

            :param complete: `jedi.api.Complete` object
            :return: tuple(string, string)
        """
        display, insert = complete.word + '\t' + complete.type, complete.word

        if not insert_funcargs:
            if complete.type == 'Function':
                # if its a function add parentheses
                return display, insert + "(${1})"
            return display, insert

        if hasattr(complete.definition, 'params'):
            params = []
            for index, param in enumerate(complete.definition.params):
                # Strip all whitespace to make it PEP8 compatible
                code = param.get_code().strip()
                code = '='.join(s.strip() for s in code.split('='))
                if code != 'self':
                    params.append("${%d:%s}" % (index + 1, code))
            insert = "%(fname)s(%(params)s)" % {
                'fname': insert,
                'params': ', '.join(params)
            }
        return display, insert

    def funcargs_from_script(self, script):
        """ get completion in case we are in a function call """
        completions = []
        in_call = script.get_in_function_call()
        if in_call is not None:
            for calldef in in_call.params:
                # Strip all whitespace to make it PEP8 compatible
                code = calldef.get_code().strip()
                if '*' in code or code == 'self':
                    continue
                code = [s.strip() for s in code.split('=')]
                if len(code) == 1:
                    completions.append((code[0], '%s=${1}' % code[0]))
                else:
                    completions.append((code[0] + '\t' + code[1],
                                       '%s=${1:%s}' % (code[0], code[1])))
        return completions

    def completions_from_script(self, script, insert_params):
        """ regular completions """
        completions = script.complete()
        completions = [self.format(complete, insert_params) for complete in completions]
        return completions


class SublimeJediComplete(JediEnvMixin, SublimeMixin, sublime_plugin.TextCommand):
    """ On "dot" completion command

        This command allow call the autocomplete command right after user put
        "." in editor.

        But user can put "." in the "string" content.
        In this case "autocomplete" have not be shown.
        For this case we are going run Jedi completion in the command, and if
        completions will been found we gonna run autocomplete command.

        To prevent Jedi overhiting, we will send completion results in the
        global namespace
    """

    def is_enabled(self):
        return True

    def is_dotcompletion_enabled(self):
        """ Return command enable status

            :return: bool
        """
        plugin_settings = get_plugin_settings()
        return plugin_settings.get('auto_complete_on_dot', True)

    def run(self, edit):
        for region in self.view.sel():
            self.view.insert(edit, region.end(), ".")

        # Hack to redisplay the completion dialog with new information
        # if it was already showing
        self.view.run_command("hide_auto_complete")

        if self.is_dotcompletion_enabled():
            sublime.set_timeout(self.delayed_complete, 1)

    def delayed_complete(self):
        global _dotcomplete
        with self.env:
            script = get_script(self.view, self.view.sel()[0].begin())
            insert_funcargs = self.is_funcargs_complete_enabled(self.view)
            _dotcomplete = self.completions_from_script(script, insert_funcargs)

        if len(_dotcomplete):
            # Only complete if there's something to complete
            self.view.run_command("auto_complete",  {
                                  'disable_auto_insert': True,
                                  'api_completions_only': True,
                                  'next_completion_if_showing': False,
                                  'auto_complete_commit_on_tab': True,
                                  })


class Autocomplete(JediEnvMixin, SublimeMixin, sublime_plugin.EventListener):

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

        # get completions list
        with self.env:
            completions = self.get_completions(view, locations)

        return completions

    def get_completions(self, view, locations):
        """ Get Jedi Completions for current `location` in the current `view`
            and return list of ('possible completion', 'completion type')

            :param view: `sublime.View` object
            :type view: sublime.View
            :param locations: offset from beginning
            :type locations: int

            :return: list
        """
        global _dotcomplete

        # reuse previously cached completion result
        if len(_dotcomplete) > 0:
            completions = _dotcomplete
        else:
            # get a completions
            script = get_script(view, locations[0])
            insert_funcargs = self.is_funcargs_complete_enabled(view)
            completions = self.funcargs_from_script(script) or \
                self.completions_from_script(script, insert_funcargs)

        _dotcomplete = []
        return completions
