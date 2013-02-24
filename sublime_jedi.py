import sublime
import sublime_plugin

import json
import sys
import re
import traceback
import copy
import subprocess
import jedi

LANGUAGE_REGEX = re.compile("(?<=source\.)[\w+#]+")

#import pprint
#jedi.debug.debug_function = lambda level, *x: pprint.pprint((repr(level), x))

_dotcomplete = []


def get_sys_path(python_interpreter):
    """ Get PYTHONPATH for passed interpreter and return it

        :param python_interpreter: python interpreter path
        :type python_interpreter: unicode or buffer

        :return: list
    """
    command = [python_interpreter, '-c', "import sys; print sys.path"]
    process = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE)
    out = process.communicate()[0]
    sys_path = json.loads(out.replace("'", '"'))
    return sys_path


def get_user_env():
    """ Gets user's interpreter from the settings and returns
        PYTHONPATH for this interpreter

        TODO: add possibility cache project PYTHONPATH

        :return: list
    """
    # load settings
    plugin_settings = sublime.load_settings(__name__ + '.sublime-settings')
    project_settings = sublime.active_window().active_view().settings()

    # get user interpreter, or get system default
    interpreter_path = project_settings.get(
        'python_interpreter_path',
        plugin_settings.get('python_interpreter_path')
        )

    sys_path = get_sys_path(interpreter_path)

    # get user interpreter, or get system default
    package_paths = project_settings.get(
        'python_package_paths',
        plugin_settings.get('python_package_paths')
        )

    # extra paths should in the head on the sys.path list
    # to override "default" packages from in the environment
    sys_path = sys_path + package_paths

    return sys_path


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
        text.encode("utf-8"),
        current_line + 1,
        current_column,
        source_path.encode("utf-8")
    )
    return script


def get_language(view):
    caret = view.sel()[0].a
    language = LANGUAGE_REGEX.search(view.scope_name(caret))
    if language is None:
        return None
    return language.group(0)


def format(complete):
    """ Returns a tuple of the string that would be visible in the completion
        dialogue, and the snippet to insert for the completion

        :param complete: `jedi.api.Complete` object
        :return: tuple(string, string)
    """
    root = complete.name
    display, insert = complete.word, complete.word
    p = None
    while isinstance(root, jedi.evaluate.ArrayElement):
        root = root.parent()

    if isinstance(root, jedi.keywords.Keyword):
        display += "\tkeyword"
    else:
        p = root.get_parent_until(
            [
                jedi.parsing.Import,
                jedi.parsing.Statement,
                jedi.parsing.Class,
                jedi.parsing.Function, jedi.evaluate.Function
            ])

    if p:
        if p.isinstance(jedi.parsing.Function, jedi.evaluate.Function):
            try:
                cls = root.get_parent_until([jedi.evaluate.Instance])
                params = list(p.params)

                def safe_name(name, idx):
                    try:
                        name = a.get_name().get_code()
                    except:
                        name = "unknown_varname%d" % idx
                    return name

                params = [safe_name(a, idx) for idx, a in enumerate(params)]
                if cls.isinstance(jedi.evaluate.Instance):
                    # Remove "self"
                    try:
                        params.remove(cls.get_func_self_name(p))
                    except:
                        pass
            except:
                traceback.print_exc()
                params = []

            insert = "%(fname)s(%(params)s)" % {
                'fname': p.name,
                'params': ', '.join(["${%d:%s}" % (x + 1, par)
                                     for x, par in enumerate(params)])
            }

        display += "\t"
        display += str(complete.type)

    return display, insert


class JediEnvMixin(object):
    """ Mixin to install user virtual env for JEDI """

    def install_env(self):
        env = get_user_env()
        self._origin_env = copy.copy(sys.path)
        sys.path = copy.copy(env)

    def restore_env(self):
        if self._origin_env:
            sys.path = copy.copy(self._origin_env)
            del self._origin_env


class SublimeJediComplete(JediEnvMixin, sublime_plugin.TextCommand):
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
        plugin_settings = sublime.load_settings(__name__ + '.sublime-settings')
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

        # install user env
        self.install_env()

        script = get_script(self.view, self.view.sel()[0].begin())
        _dotcomplete = script.complete()

        # restore sublime env
        self.restore_env()

        if len(_dotcomplete):
            # Only complete if there's something to complete
            self.view.run_command("auto_complete")
            self.view.run_command("auto_complete",  {
                            'disable_auto_insert': True,
                            'api_completions_only': True,
                            'next_completion_if_showing': False,
                            'auto_complete_commit_on_tab': True,
                        })


class Autocomplete(JediEnvMixin, sublime_plugin.EventListener):

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
        if get_language(view) != "python":
            return None

        # install user env
        self.install_env()

        # get completions list
        completions = self.get_completions(view, locations)

        # restore sublime env, to keep functionality
        self.restore_env()

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
            script = get_script(view, locations[0])
            completions = script.complete()

        # empty cache
        _dotcomplete = []

        # prepare jedi completions to Sublime format
        completions = [format(complete) for complete in completions]

        return completions
