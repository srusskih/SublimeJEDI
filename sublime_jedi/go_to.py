# -*- coding: utf-8 -*-
import sublime
import sublime_plugin
from functools import partial

from .utils import to_relative_path, ask_daemon, PythonCommandMixin
from .settings import get_settings_param


class BaseLookUpJediCommand(PythonCommandMixin):

    def _jump_to_in_window(self, filename, line_number=None, column_number=None, transient=False):
        """ Opens a new window and jumps to declaration if possible

            :param filename: string or int
            :param line_number: int
            :param column_number: int
            :param transient: bool

            If transient is True, opens a transient view
        """
        active_window = self.view.window()

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

        flags = self.prepare_layout(active_window, transient, filename)
        active_window.open_file('%s:%s:%s' % (filename, line_number or 0,
                                column_number or 0), flags)

    def prepare_layout(self, window, transient, filename):
        """
        prepares the layout of the window to configured and returns flags
        for opening the file
        """
        flags = sublime.ENCODED_POSITION
        if transient:
            flags |= sublime.TRANSIENT
            # sublime cant show quick panel with options on one panel and
            # file's content in transient mode on another panel
            # so dont do anything if its a requrest to show just options
            return flags
        goto_layout = get_settings_param(self.view, 'sublime_goto_layout')
        if goto_layout == 'single-panel-transient' and not transient:
            flags |= sublime.TRANSIENT
        elif goto_layout == 'two-panel':
            self.switch_to_two_panel_layout(window, filename)
        elif goto_layout == 'two-panel-transient':
            self.switch_to_two_panel_layout(window, filename)
            if not transient:
                flags |= sublime.TRANSIENT
        return flags

    def switch_to_two_panel_layout(self, window, filename):
        curr_group = window.active_group()
        layout = window.get_layout()
        if len(layout['cells']) == 1:
            # currently a single panel layout so switch to two panels
            window.set_layout({
                'cols': [0.0, 0.5, 1.0],
                'rows': [0.0, 1.0],
                'cells': [[0, 0, 1, 1], [1, 0, 2, 1]],
            })
        # select non current group(panel)
        selected_group = None
        for group in range(window.num_groups()):
            if group != curr_group:
                selected_group = group
                window.focus_group(group)
                break
        # if the file is already opened and is in current group
        # move it to another panel.
        files_in_curr_group = dict([
            (i.file_name(), i) for i in
            window.views_in_group(curr_group)
        ])
        if filename and filename in files_in_curr_group:
            if files_in_curr_group[filename].view_id != self.view.view_id:
                window.set_view_index(files_in_curr_group[filename], selected_group, 0)

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
