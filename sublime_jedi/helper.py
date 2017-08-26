# -*- coding: utf-8 -*-
from functools import partial

import sublime
import sublime_plugin

from .console_logging import getLogger

logger = getLogger(__name__)

from .settings import get_plugin_settings
from .utils import (
    ask_daemon, is_python_scope, is_sublime_v2, PythonCommandMixin
)
try:
    from .tooltips import show_docstring_tooltip
except ImportError as e:
    logger.debug('Unable to import tooltips: %s %s' % (type(e), e.message))
    logger.warning('Tooltips disabled for ST2.')




class HelpMessageCommand(sublime_plugin.TextCommand):
    """Command to insert docstring into Sublime output panel."""

    def run(self, edit, docstring):
        self.view.insert(edit, self.view.size(), docstring)


def show_docstring_panel(view, docstring):
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


class SublimeJediDocstring(PythonCommandMixin, sublime_plugin.TextCommand):
    """Show docstring."""

    def run(self, edit):
        ask_daemon(self.view, self.render, 'docstring')

    def render(self, view, docstring):
        if docstring is None or docstring == '':
            logger.debug('Empty docstring.')
            return

        if is_sublime_v2():
            show_docstring_panel(view, docstring)
        else:
            show_docstring_tooltip(view, docstring)


class SublimeJediSignature(PythonCommandMixin, sublime_plugin.TextCommand):
    """Show signature in status bar."""

    def run(self, edit):
        ask_daemon(self.view, self.show_signature, 'signature')

    def show_signature(self, view, signature):
        if signature:
            sublime.status_message('Jedi: {0}'.format(signature))


class SublimeJediTooltip(sublime_plugin.EventListener):
    """EventListener to show jedi's docstring tooltip."""

    # display tooltip only for
    #  - function/variable usage (variable.function, variable.other)
    #  - function/variable definition (entity.name.class, entity.name.function)
    SELECTOR = 'source.python & (variable | entity.name)'

    def enabled(self):
        """Check if hover popup is desired."""
        return get_plugin_settings().get('enable_tooltip', True)

    def on_activated(self, view):
        """Handle view.on_activated event."""
        if not (self.enabled() and view.match_selector(0, 'source.python')):
            return

        # disable default goto definition popup
        view.settings().set('show_definitions', False)

    def on_hover(self, view, point, hover_zone):
        """Handle view.on_hover event."""
        if not (hover_zone == sublime.HOVER_TEXT and self.enabled() and
                view.match_selector(point, self.SELECTOR)):
            return

        ask_daemon(view,
                   partial(show_docstring_tooltip, location=point),
                   'docstring',
                   point)
