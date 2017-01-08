# -*- coding: utf-8 -*-
import sublime
import sublime_plugin

from .console_logging import getLogger
from .utils import ask_daemon, PythonCommandMixin, is_sublime_v2

logger = getLogger(__name__)


class HelpMessageCommand(sublime_plugin.TextCommand):

    def run(self, edit, docstring):
        self.view.insert(edit, self.view.size(), docstring)


def docstring_panel(view, docstring):
    """Show docstring in output panel.

    :param view (sublime.View): current active view
    :param docstring (basestring): python __doc__ string
    """
    window = sublime.active_window()

    if docstring:
        output = window.get_output_panel('help_panel')
        output.set_read_only(False)
        output.run_command('help_message', {'docstring': docstring})
        output.set_read_only(True)
        window.run_command('show_panel', {'panel': 'output.help_panel'})
    else:
        window.run_command('hide_panel', {'panel': 'output.help_panel'})
        sublime.status_message('Jedi: No results!')


def docstring_tooltip(view, docstring, content_builder):
    """Show docstring in popup.

    :param view (sublime.View): current active view
    :param docstring (basestring): python __doc__ string
    :param content_builder (callable): callable object should accept docstring
        and return content read for popup (a html text)
    """
    if docstring:
        content = content_builder(docstring)
        view.show_popup(content, max_width=512)
    else:
        sublime.status_message('Jedi: No results!')


def simple_html_builder(docstring):
    docstring = docstring.split('\n')
    docstring[0] = '<b>' + docstring[0] + '</b>'
    html = '<body><p style="font-family: sans-serif; font-family: sans-serif;">{0}</p></body>'.format(
       '<br />'.join(docstring)
    )
    return html


class SublimeJediDocstring(PythonCommandMixin, sublime_plugin.TextCommand):
    """Show docstring."""

    def run(self, edit):
        ask_daemon(self.view, self.render, 'docstring')

    def render(self, view, docstring):
        if is_sublime_v2():
            docstring_panel(view, docstring)
        else:
            docstring_tooltip(view, docstring, simple_html_builder)


class SublimeJediSignature(PythonCommandMixin, sublime_plugin.TextCommand):
    """
    Show signature in status bar
    """
    def run(self, edit):
        ask_daemon(self.view, self.show_signature, 'signature')

    def show_signature(self, view, signature):
        if signature:
            sublime.status_message('Jedi: {0}'.format(signature))
