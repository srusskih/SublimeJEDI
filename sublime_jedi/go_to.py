# -*- coding: utf-8 -*-
import sublime
import sublime_plugin
from functools import partial

from .utils import to_relative_path, ask_daemon, is_python_scope


class BaseLookUpJediCommand(object):

    def is_enabled(self):
        """ command enable only for python source code """
        if not is_python_scope(self.view, self.view.sel()[0].begin()):
            return False
        return True

    def _jump_to_in_window(self, filename, line_number=None, column_number=None, transient=False):
        """ Opens a new window and jumps to declaration if possible

            :param filename: string or int
            :param line_number: int
            :param column_number: int
            :param transient: bool

            If transient is True, opens a transient view
        """
        active_window = sublime.active_window()

        # restore saved location
        try:
            if self.view.sel()[0] != self.point:
                self.view.sel().clear()
                self.view.sel().add(self.point)
        except AttributeError:
            # called without setting self.point
            pass

        # If the file was selected from a drop down list
        if isinstance(filename, int):
            if filename == -1:  # cancelled
                # restore view
                active_window.focus_view(self.view)
                self.view.show(self.point)
                return
            filename, line_number, column_number = self.options[filename]
        flags = sublime.ENCODED_POSITION
        if transient:
            flags |= sublime.TRANSIENT
        active_window.open_file('%s:%s:%s' % (filename, line_number or 0,
                                column_number or 0), flags)

    def _window_quick_panel_open_window(self, view, options):
        """ Shows the active `sublime.Window` quickpanel (dropdown) for
            user selection.

            :param option: list of `jedi.api_classes.BasDefinition`
        """
        active_window = view.window()

        # remember filenames
        self.options = options

        # remember current file location
        self.point = self.view.sel()[0]

        # Show the user a selection of filenames
        active_window.show_quick_panel(
            [self.prepare_option(o) for o in options],
            self._jump_to_in_window, 
            on_highlight=partial(self._jump_to_in_window, transient=True))

    def prepare_option(self, option):
        """ prepare option to display out in quick panel """
        raise NotImplementedError(
            "{} require `prepare_option` definition".format(self.__class__)
        )


class SublimeJediGoto(BaseLookUpJediCommand, sublime_plugin.TextCommand):
    """
    Go to object definition
    """
    def run(self, edit):
        ask_daemon(self.view, self.handle_definitions, 'goto')

    def handle_definitions(self, view, defns):
        if not defns:
            return False
        if len(defns) == 1:
            defn = defns[0]
            self._jump_to_in_window(*defn)
        else:
            self._window_quick_panel_open_window(view, defns)

    def prepare_option(self, option):
        return to_relative_path(option[0])


class SublimeJediFindUsages(BaseLookUpJediCommand, sublime_plugin.TextCommand):
    """
    Find object usages
    """
    def run(self, edit):
        ask_daemon(self.view, self._window_quick_panel_open_window, 'usages')

    def prepare_option(self, option):
        return [to_relative_path(option[0]),
                "line: %d column: %d" % (option[1], option[2])]
