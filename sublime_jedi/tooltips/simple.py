# -*- coding: utf-8 -*-
import html

from .base import Tooltip


class SimpleTooltip(Tooltip):

    @classmethod
    def guess(cls, docstring):
        return True

    def _build_html(self, docstring):
        docstring = html.escape(docstring, quote=False).split('\n')
        docstring[0] = '<b>' + docstring[0] + '</b>'
        content = '<body><p style="font-family: sans-serif;">{0}</p></body>'.format(
           '<br />'.join(docstring)
        )
        return content

    def show_popup(self, view, docstring, location=None):
        if location is None:
            location = view.sel()[0].begin()

        content = self._build_html(docstring)
        view.show_popup(content, location=location, max_width=512)
