# -*- coding: utf-8 -*-
try:
    from typing import Set, List, Tuple, Any
except Exception:
    pass

import sublime
import sublime_plugin
from functools import partial
import re

from .utils import to_relative_path, PythonCommandMixin, get_settings, is_python_scope, debounce
from .daemon import ask_daemon
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
        follow_imports = get_settings(self.view)['follow_imports']
        ask_daemon(
            self.view,
            self.handle_definitions,
            'goto',
            ask_kwargs={
                'follow_imports': follow_imports
            },
        )

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
    Find object usages, and optionally rename objects.
    """
    def run(self, edit):
        self.edit = edit
        ask_daemon(self.view, self.handle_usages, 'usages')

    def handle_usages(self, view, options) -> None:
        if not options:
            return

        active_window = view.window()

        # remember filenames
        self.options = options

        # remember current file location
        self.point = self.view.sel()[0]

        # expands selection to all of "focused" symbol
        name = expand_selection(self.view, self.point)

        def handle_rename(new_name: str) -> None:
            groups = []  # type: List[List[Tuple[str, int, int]]]
            files = set()  # type: Set[str]

            for option in options:
                file = option[0]
                if not file:  # can't replace text (or even show usages) in unsaved file
                    continue
                if file in files:
                    groups[-1].append(option)
                else:
                    groups.append([option])
                files.add(file)

            for group in groups:
                rename_in_file(group, group[0][0], new_name)

        def rename_in_file(group, file_, new_name):
            # type: (List[Tuple[str, int, int]], str, str) -> None
            with open(file_) as f:
                text = f.read()
            original_text = text
            offset = 0

            for option in group:
                assert text and name
                _, row, col = option
                point = text_point(original_text, row-1, col-1)

                text = text[:point + offset] + new_name + text[point + offset + len(name):]
                offset += len(new_name) - len(name)

            with open(file_, "w") as f:
                f.write(text)

        def handle_choose(idx):
            if not name:
                return
            if idx == 0:
                view.window().show_input_panel("New name:", name, handle_rename, None, None)
                return
            self._jump_to_in_window(idx - 1 if idx != -1 else idx)

        def handle_highlight(idx):
            if idx == 0:
                return
            self._jump_to_in_window(idx - 1 if idx != -1 else idx, transient=True)

        # Show the user a selection of filenames
        files = {option[0] for option in options}  # type: Set[str]
        first_option = [[
            'rename "{}"'.format(name),
            "{} occurrence{} in {} file{}".format(
                len(options), 's' if len(options) != 1 else '', len(files), 's' if len(files) != 1 else '')
        ]]
        active_window.show_quick_panel(
            first_option + [self.prepare_option(o) for o in options],
            handle_choose,
            on_highlight=handle_highlight)

    def prepare_option(self, option):
        return [to_relative_path(option[0]),
                "line: %d column: %d" % (option[1], option[2])]


def expand_selection(view, point):
    # type: (Any, Any) -> str
    name = ""
    _, col = view.rowcol(point.begin())
    for match in re.finditer(r"[A-Za-z0-9_]+", view.substr(view.line(point.begin()))):
        if match.start() <= col and match.end() >= col:
            name = match.group()
    return name


def text_point(text: str, row: int, col: int) -> int:
    """
    Return the integer offset for the char at 0-indexed row and col in text.
    Similar to View.text_point, but doesn't require loading the view first.
    """
    chars = 0
    for line in text.splitlines()[:row]:
        chars += len(line) + 1
    return chars + col


class SublimeJediEventListener(sublime_plugin.EventListener):

    def on_selection_modified_async(self, view) -> None:
        should_highlight = get_settings_param(view, 'highlight_usages_on_select')
        if not view.file_name() or not is_python_scope(view, view.sel()[0].begin()) or not should_highlight:
            return
        highlight_usages(view)


@debounce(0.35)
def highlight_usages(view) -> None:
    ask_daemon(view, handle_highlight_usages, 'usages')


def handle_highlight_usages(view, options):
    # type: (Any, List[Tuple[str, int, int]]) -> None
    name = expand_selection(view, view.sel()[0])
    file_name = view.file_name()

    def get_region(o):
        # type: (Tuple[str, int, int]) -> Any
        _, row, col = o
        point = view.text_point(row-1, col-1)
        return sublime.Region(point, point + len(name))

    regions = [get_region(o) for o in options if o[0] == file_name]

    if not regions:
        view.erase_regions('sublime-jedi-usages')
        return

    highlight_color = get_settings_param(view, 'highlight_usages_color')

    view.add_regions("sublime-jedi-usages", regions, highlight_color or "region.bluish",
                     flags=sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SOLID_UNDERLINE)
