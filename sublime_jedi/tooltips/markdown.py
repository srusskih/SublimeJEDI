# -*- coding: utf-8 -*-
import html

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

    def _build_html(self, view, docstring):
        """ Convert python docstring to text ready to show in popup.
        
        :param view: sublime text view object
        :param docstring: python docstring as a string
        """
        doclines = docstring.split('\n')
        signature = doclines[0].strip()
        # first line is a signature if it contains parentheses
        if '(' in signature:

            def is_class(string):
                """Check whether string contains a class or function signature."""
                for c in string:
                    if c != '_':
                        break
                return c.isupper()

            # a hackish way to determine whether it is a class or function
            prefix = 'class' if is_class(signature) else 'def'
            # highlight signature
            content = '```python\n{0} {1}\n```\n'.format(prefix, signature)
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

    def show_popup(self, view, docstring, location=None):
        if location is None:
            location = view.sel()[0].begin()

        mdpopups.show_popup(
            view=view,
            content=self._build_html(view, docstring),
            location=location,
            max_width=800,
            md=True,
            css=self._get_style(),
            wrapper_class='jedi',
            flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY)

