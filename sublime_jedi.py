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


def get_settings_param(view, param_name, default=None):
    plugin_settings = get_plugin_settings()
    project_settings = view.settings()
    return project_settings.get(
        param_name,
        plugin_settings.get(param_name, default)
    )


def get_function_parameters(callDef):
    """ (jedi.api_classes.CallDef) -> list of tuple(str, str)

    Return list function paramets, prepared for sublime completion.
    Tuple contains parameter name and default value

    Parameters list excludes: self, *args and **kwargs parameters
    """
    if not callDef:
        return []

    params = []
    for param in callDef.params:
        cleaned_param = param.get_code().strip()
        if '*' in cleaned_param or cleaned_param == 'self':
            continue
        params.append([s.strip() for s in cleaned_param.split('=')])
    return params


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
    """
    helpers to integrate sublime
    """
    def is_funcargs_complete_enabled(self, view):
        return get_settings_param(view, 'auto_complete_function_params')

    def is_funcargs_all_complete_enabled(self, view):
        return get_settings_param(view, 'auto_complete_function_params') == "all"

    def format(self, complete):
        """ Returns a tuple of the string that would be visible in
            the completion dialogue and the completion word

            :param complete: `jedi.api.Complete` object
            :return: tuple(string, string)
        """
        display, insert = complete.word + '\t' + complete.type, complete.word
        return display, insert

    def funcargs_from_script(self, script):
        """ get completion in case we are in a function call """
        completions = []
        in_call = script.function_definition()

        params = get_function_parameters(in_call)
        for code in params:
            if len(code) == 1:
                completions.append((code[0], '%s=${1}' % code[0]))
            else:
                completions.append((code[0] + '\t' + code[1],
                                   '%s=${1:%s}' % (code[0], code[1])))
        return completions

    def completions_from_script(self, script, view):
        """ regular completions """
        completions = script.complete()
        completions = [self.format(complete) for complete in completions]
        return completions


class SublimeJediParamsAutocomplete(JediEnvMixin, SublimeMixin,
                                    sublime_plugin.TextCommand):
    """
    Function / Class constructor autocompletion command
    """
    def run(self, edit, characters='('):
        regions = [a for a in self.view.sel()]
        self.view.sel().clear()

        is_enabled = self.is_funcargs_complete_enabled(self.view)

        for region in reversed(regions):
            position = 0
            if region.size() > 0:
                self.view.replace(edit, region, characters)
                position = region.begin() + len(characters)
            else:
                self.view.insert(edit, region.end(), characters + ')')
                position = region.end() + len(characters)

            self.view.sel().add(sublime.Region(position, position))

            # if function arguemtns completion enabled
            # return list of function args
            if is_enabled:
                with self.env:
                    self.get_complete(position)

    def get_complete(self, position):
        complete_all = self.is_funcargs_all_complete_enabled(self.view)
        script = get_script(self.view, position)
        parameters = get_function_parameters(script.function_definition())

        completions = []
        for index, parameter in enumerate(parameters):
            name = parameter[0]
            if len(parameter) > 1 and complete_all:
                value = parameter[1]
                completions.append('%s=${%d:%s}' % (name, index + 1, value))
            elif len(parameter) == 1:
                completions.append('%s=${%d}' % (name, index + 1))

        template = ", ".join(completions)
        self.view.run_command('insert_snippet', {"contents": template})


class Autocomplete(JediEnvMixin, SublimeMixin, sublime_plugin.EventListener):
    """
    Sublime Text autocompletion integration
    """
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
        script = get_script(view, locations[0])
        completions = self.completions_from_script(script, view) +\
            self.funcargs_from_script(script)

        return completions
