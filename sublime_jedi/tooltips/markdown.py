# -*- coding: utf-8 -*-
import html
import re

import sublime

try:
    # mdpopups needs 3119+ for wrapper_class, which diff popup relies on
    if int(sublime.version()) < 3119:
        raise ImportError('Sublime Text 3119+ required.')

    import mdpopups

    # mdpopups 1.9.0+ is required because of wrapper_class and templates
    if mdpopups.version() < (1, 9, 0):
        raise ImportError('mdpopups 1.9.0+ required.')

    _HAVE_MDPOPUPS = True
except ImportError:
    _HAVE_MDPOPUPS = False

from .base import Tooltip


class MarkDownTooltip(Tooltip):

    @classmethod
    def guess(cls, docstring):
        return _HAVE_MDPOPUPS

    def _get_style(self):
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
        return css

    def _prepare_signatire(self, signature):
        """Parse string and prepend def/class keyword for valid signature.

        :param signature: The string parse and check whether it is a signature.

        :returns: None string or the prefixed signature
        """
        pattern = '^([\w\. \t]+\.[ \t]*)?(\w+)\('
        match = re.match(pattern, signature)

        if not match:
            return None

        # lower case built-in types
        path, func = match.groups()
        types = (
            'basestring', 'unicode', 'byte', 'dict', 'float', 'int',
            'list', 'tuple', 'str', 'set', 'frozenset')
        if any(func.startswith(s) for s in types):
            prefix = ''
        else:
            func = func.lstrip('_')
            prefix = 'class ' if func[0].isupper() else 'def '

        return prefix + signature

    def _build_html(self, view, docstring):
        """Convert python docstring to text ready to show in popup.

        :param view: sublime text view object
        :param docstring: python docstring as a string
        """
        doclines = docstring.split('\n')
        signature = self._prepare_signatire(doclines[0])
        # first line is a signature if it contains parentheses
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
            'Args:', 'Arguments:', 'Attributes:', 'Example:', 'Examples:',
            'Note:', 'Raises:', 'Returns:', 'Yields:')
        for keyword in keywords:
            content = content.replace(
                keyword + '<br />', '<h6>' + keyword + '</h6>')
        return content

    def show_popup(self, view, docstring, location=None):
        if location is None:
            location = view.sel()[0].begin()

        mdpopups.show_popup(
            view=view,
            content=self._build_html(view, docstring),
            location=location,
            max_width=int(view.viewport_extent()[0]),
            md=True,
            css=self._get_style(),
            wrapper_class='jedi',
            flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY)
