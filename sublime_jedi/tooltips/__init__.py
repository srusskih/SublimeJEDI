# -*- coding: utf-8 -*-

from .markdown import MarkDownTooltip
from .simple import SimpleTooltip


def _guess_docstring_format(docstring):
    """Find proper tooltip class for docstring.

    Docstrings could has different format, and we should pick a proper
    tooltip for it.

    :rtype: sublime_jedi.tooltips.base.Tooltip
    """
    for tooltip_class in [MarkDownTooltip]:
        if tooltip_class.guess(docstring):
            return tooltip_class()

    return SimpleTooltip()


def show_docstring_tooltip(view, docstring, location=None):
    """Show docstring in popup.

    :param view (sublime.View): current active view
    :param docstring (basestring): python __doc__ string
    :param location (int): The text point where to create the popup
    """
    if docstring:
        tooltip = _guess_docstring_format(docstring)
        tooltip.show_popup(view, docstring, location)
