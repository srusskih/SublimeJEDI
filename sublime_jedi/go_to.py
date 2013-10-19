# -*- coding: utf-8 -*-
import sublime
import sublime_plugin

from .utils import to_relative_path, ask_daemon, is_python_scope


class BaseLookUpJediCommand(object):

    def is_enabled(self):
        """ command enable only for python source code """
        if not is_python_scope(self.view, self.view.sel()[0].begin()):
            return False
        return True

    def _jump_to_in_window(self, filename, line_number=None, column_number=None):
        """ Opens a new window and jumps to declaration if possible

            :param filename: string or int
            :param line_number: int
            :param column_number: int
        """
        active_window = sublime.active_window()

        # If the file was selected from a drop down list
        if isinstance(filename, int):
            if filename == -1:  # cancelled
                return
            filename, line_number, column_number = self.options[filename]
        active_window.open_file('%s:%s:%s' % (filename, line_number or 0,
                                column_number or 0), sublime.ENCODED_POSITION)

    def _window_quick_panel_open_window(self, view, options):
        """ Shows the active `sublime.Window` quickpanel (dropdown) for
            user selection.

            :param option: list of `jedi.api_classes.BasDefinition`
        """
        active_window = view.window()

        # remember filenames
        self.options = options

        # Show the user a selection of filenames
        active_window.show_quick_panel(
            [self.prepare_option(o) for o in options],
            self._jump_to_in_window
        )

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
