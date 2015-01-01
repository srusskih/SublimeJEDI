# -*- coding: utf-8 -*-
import sublime
import sublime_plugin

from .utils import ask_daemon


class HelpMessageCommand(sublime_plugin.TextCommand):

    def run(self, edit, docstring):
        self.view.close()
        self.view.insert(edit, self.view.size(), docstring)


class SublimeJediDocstring(sublime_plugin.TextCommand):
    """
    Show doctring in output panel
    """
    def run(self, edit):
        ask_daemon(self.view, self.show_docstring, 'docstring')

    def show_docstring(self, view, docstring):
        window = sublime.active_window()
        if docstring:
            output = window.get_output_panel('help_panel')
            output.set_read_only(False)
            output.run_command('help_message', {'docstring': docstring})
            output.set_read_only(True)
            window.run_command("show_panel", {"panel": "output.help_panel"})
        else:
            window.run_command("hide_panel", {"panel": "output.help_panel"})
            sublime.status_message('Jedi: No results!')


class SublimeJediSignature(sublime_plugin.TextCommand):
    """
    Show signature in statusbar
    """
    def run(self, edit):
        ask_daemon(self.view, self.show_signature, 'signature')

    def show_signature(self, view, signature):
        if signature:
            sublime.status_message('Jedi: {0}'.format(signature))
