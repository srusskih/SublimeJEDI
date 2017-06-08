# -*- coding: utf-8 -*-
import abc


class Tooltip:

    __metaclass__ = abc.ABCMeta  # works for 2.7 and 3+

    @classmethod
    @abc.abstractmethod
    def guess(cls, docstring):
        """Check if tooltip can render the docstring.

        :rtype: bool
        """

    @abc.abstractmethod
    def show_popup(self, view, docstring, location=None):
        """Show tooltip with docstring.

        :rtype: NoneType
        """
