import sublime
import sublime_plugin

from sublime_jedi import get_script, JediEnvMixin
from jedi.api import NotFoundError


def check_if_string(view):
    """ Checks if the current selection is a string

        :param view: `sublime.View` object

        :return: bool
    """
    sels = view.sel()
    region = view.word(sels[0])

    line = view.line(region)
    currently_string = False
    current_string_quotes = []

    for x in range(line.a, line.b):
        char = view.substr(x)
        if char in ('\'', '"'):

            if len(current_string_quotes) == 1 and current_string_quotes[-1] == char:
                currently_string = False
                current_string_quotes.pop()

            else:
                currently_string = True
                current_string_quotes.append(char)

        if x >= region.a:
            return currently_string

    return currently_string


class SublimeJediGoto(JediEnvMixin, sublime_plugin.TextCommand):

    def run(self, edit):

        # If we have a string, dispatch it elsewhere
        if check_if_string(self.view):
            self.view.run_command('string_go_to')
            return

        with self.env:
            script = get_script(self.view, self.view.sel()[0].begin())

            # If we have a possible python declaration
            # use jedi to find possible declarations.
            # found = self.attempt_get_definition(script)
            # if not found:
            #     found = self.attempt_go_to(script)
            for method in ['get_definition', 'goto']:
                try:
                    defns = getattr(script, method)()
                except NotFoundError:
                    return
                else:
                    self.handle_definitions(defns)
                    break

    def handle_definitions(self, defns):
        # filter out builtin
        self.defns = [i for i in defns if not i.in_builtin_module()]
        if not self.defns:
            return False
        if len(self.defns) == 1:
            defn = self.defns[0]
            self._jump_to_in_window(defn.module_path, defn.start_pos[0], defn.start_pos[1])
        else:
            self._window_quick_panel_open_window(self.defns)

    def _jump_to_in_window(self, filename, line_number=None, column_number=None):
        """ Opens a new window and jumps to declaration if possible

            :param filename: string or int
            :param line_number: int
            :param column_number: int
        """
        active_window = self.view.window()

        # If the file was selected from a drop down list
        if isinstance(filename, int):
            if filename == -1:  # cancelled
                return
            line_number, column_number = self.options_map[filename]
        active_window.open_file('%s:%s:%s' % (filename, line_number or 0,
                                column_number or 0), sublime.ENCODED_POSITION)

    def _window_quick_panel_open_window(self, options):
        """ Shows the active `sublime.Window` quickpanel (dropdown) for
            user selection.

            :param option: list of `jedi.api_classes.Definition`
        """

        active_window = self.view.window()

        # Map the filenames to line and column numbers
        self.options_map = dict((o.module_path, (o.start_pos[0], o.start_pos[1]))
                                     for o in self.defns)

        # Show the user a selection of filenames
        active_window.show_quick_panel(self.defns, self._jump_to_in_window)
