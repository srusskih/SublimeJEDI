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
            .jedi .highlight {
                font-size: 1.1rem;
            }
        """
        return css

    def _prepare_signature(self, docstring):
        """Parse string and prepend def/class keyword for valid signature.

        :param docstring: The string to extract the signature from.

        :returns: None string or the prefixed signature
        """
        pattern = (
            '(?x)'
            '^([\w\. \t]+\.[ \t]*)?'    # path
            '(\w+)'                     # function / object
            '[ \t]*(\([^\)]*\))'        # arguments
            '(?:'
            '(\s*->\s*.*?)'             # annotation: -> Type
            '(--|$)'                    # inline comment: -- blabla
            ')?'
        )
        match = re.match(pattern, docstring, re.MULTILINE)
        if not match:
            return (None, docstring)

        # lower case built-in types
        path, func, args, note, comment = match.groups()
        types = (
            'basestring', 'unicode', 'byte', 'dict', 'float', 'int',
            'list', 'tuple', 'str', 'set', 'frozenset')
        if any(func.startswith(s) for s in types):
            prefix = ''
        else:
            prefix = 'class ' if func.lstrip('_')[0].isupper() else 'def '

        # join signature
        signature = ''.join(
            (prefix, path or '', func or '', args or '', note or ''))
        # Signature may span multiple lines which need to be merged to one.
        signature = signature.replace('\n', ' ')
        # Everything after the signature is docstring
        docstring = docstring[
            len(signature) + len(comment or '') - len(prefix):] or ''
        return (signature, docstring.strip())

    def _build_html(self, view, docstring):
        """Convert python docstring to text ready to show in popup.

        :param view: sublime text view object
        :param docstring: python docstring as a string
        """
        # highlight signature
        signature, docstring = self._prepare_signature(docstring)
        if signature:
            content = '```python\n{0}\n```\n'.format(signature)
        else:
            content = ''
        # merge the rest of the docstring beginning with 3rd line
        # skip leading and tailing empty lines
        content += html.escape(docstring, quote=False)
        # preserve empty lines
        content = content.replace('\n\n', '\n\u00A0\n')
        # preserve whitespace
        content = content.replace('  ', '\u00A0\u00A0')
        # convert markdown to html
        content = mdpopups.md2html(view, content)
        # TODO: move to GoogleStyleTooltip
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
