# -*- coding: utf-8 -*-
import html
import re

import sublime
import sublime_plugin

try:
    # mdpopups needs 3119+ for wrapper_class, which diff popup relies on
    if int(sublime.version()) < 3119:
        raise ImportError('Sublime Text 3119+ required.')
    # mdpopups 1.9.0+ is required because of wrapper_class and templates
    import mdpopups
    if mdpopups.version() < (1, 9, 0):
        raise ImportError('mdpopups 1.9.0+ required.')
    _HAVE_MDPOPUPS = True
except ImportError:
    _HAVE_MDPOPUPS = False

from .console_logging import getLogger
from .settings import get_plugin_settings
from .utils import ask_daemon, PythonCommandMixin, is_sublime_v2, is_python_scope

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


def docstring_tooltip(view, docstring, location=None):
    """Show docstring in popup.

    :param view (sublime.View): current active view
    :param docstring (basestring): python __doc__ string
    :param location (int): The text point where to create the popup
    """
    if not docstring:
        return sublime.status_message('Jedi: No results!')

    if location is None:
        location = view.sel()[0].begin()

    # fallback if mdpopups is not available
    if not _HAVE_MDPOPUPS:
        return docstring_tooltip_simple(view, docstring, location)
    #use mdpopups by default
    return docstring_tooltip_markdown(view, docstring, location)


def docstring_tooltip_markdown(view, docstring, location):
    """Show docstring in popup using mdpopups and markdown renderer.

    :param view (sublime.View): current active view
    :param docstring (basestring): python __doc__ string
    :param location (int): The text point where to create the popup
    """
    css = """
        body {
            margin: 6px;
        }
        div.mdpopups {
            margin: 0;
            padding: 0;
        }
        .jedi h6 {
            font-weight: bold;
            color: var(--bluish);
        }
    """
    return mdpopups.show_popup(
        view=view,
        content=markdown_html_builder(view, docstring),
        location=location,
        max_width=800,
        md=True,
        css=css,
        wrapper_class='jedi',
        flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY)


def markdown_html_builder(view, docstring):
    doclines = docstring.split('\n')
    signature = signature_builder(doclines[0])
    if signature:
        # highlight signature
        content = '```python\n{0}\n```\n'.format(signature)
        # merge the rest of the docstring beginning with 3rd line
        # skip leading and tailing empty lines
        docstring = '\n'.join(doclines[1:]).strip()
        content += html.escape(docstring, quote=False)
    else:
        # docstring does not contain signature
        content = html.escape(docstring, quote=False)

    # preserve empty lines
    content = content.replace('\n\n', '\n\u00A0\n')
    # preserve whitespace
    content = content.replace('  ', '\u00A0\u00A0')
    # convert markdown to html
    content = mdpopups.md2html(view, content)
    # highlight headlines ( Google Python Style Guide )
    keywords = (
        'Args:', 'Arguments:', 'Attributes:', 'Example:', 'Examples:', 'Note:',
        'Raises:', 'Returns:', 'Yields:')
    for keyword in keywords:
        content = content.replace(
            keyword + '<br />', '<h6>' + keyword + '</h6>')
    return content


def docstring_tooltip_simple(view, docstring, location):
    """Show docstring in popup using simple renderer.

    :param view (sublime.View): current active view
    :param docstring (basestring): python __doc__ string
    :param location (int): The text point where to create the popup
    """
    content = simple_html_builder(docstring)
    return view.show_popup(content, location=location, max_width=512)


def simple_html_builder(docstring):
    docstring = html.escape(docstring, quote=False).split('\n')
    docstring[0] = '<b>' + docstring[0] + '</b>'
    content = '<body><p style="font-family: sans-serif;">{0}</p></body>'.format(
       '<br />'.join(docstring)
    )
    return content


def signature_builder(string):
    """Parse string and prepend def/class keyword for valid signature.

    :param string: The string parse and check whether it is a signature.

    :returns: None string or the prefixed signature
    """
    pattern = '^([\w\.]+\.)?(\w+)\('
    match = re.match(pattern, string)
    if not match:
        return None

    path, func = match.groups()
    # lower case built-in types
    types = ('dict', 'int', 'list', 'tuple', 'str', 'set', 'frozenset')
    if any(func.startswith(s) for s in types):
        prefix = ''
    else:
        func = func.lstrip('_')
        prefix = 'class ' if func[0].isupper() else 'def '

    return prefix + string


class SublimeJediDocstring(PythonCommandMixin, sublime_plugin.TextCommand):
    """Show docstring."""

    def run(self, edit):
        ask_daemon(self.view, self.render, 'docstring')

    def render(self, view, docstring):
        if is_sublime_v2():
            docstring_panel(view, docstring)
        else:
            docstring_tooltip(view, docstring)


class SublimeJediSignature(PythonCommandMixin, sublime_plugin.TextCommand):
    """Show signature in status bar."""

    def run(self, edit):
        ask_daemon(self.view, self.show_signature, 'signature')

    def show_signature(self, view, signature):
        if signature:
            sublime.status_message('Jedi: {0}'.format(signature))


class SublimeJediTooltip(sublime_plugin.EventListener):
    """EventListener to show jedi's docstring tooltip."""

    def enabled(self):
        """Check if hover popup is desired."""
        return get_plugin_settings().get('enable_tooltip', True)

    def on_activated(self, view):
        """Handle view.on_activated event."""
        if not self.enabled():
            return
        if not view.match_selector(0, 'source.python'):
            return
        # disable default goto definition popup
        view.settings().set('show_definitions', False)

    def on_hover(self, view, point, hover_zone):
        """Handle view.on_hover event."""
        if hover_zone != sublime.HOVER_TEXT:
            return
        if not self.enabled():
            return
        if not is_python_scope(view, point):
            return

        def render(view, docstring):
            docstring_tooltip(view, docstring, point)
        ask_daemon(view, render, 'docstring', point)
