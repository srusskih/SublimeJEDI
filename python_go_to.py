import sublime
import sublime_plugin

from sublime_jedi import get_script, JediEnvMixin

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

class PythonGoTo(JediEnvMixin, sublime_plugin.TextCommand):

    def run(self, edit):

        # If we have a string, dispatch it elsewhere
        if check_if_string(self.view):
            self.view.run_command('string_go_to')
            return

        # install user env
        self.install_env()

        script = get_script(self.view, self.view.sel()[0].begin())

        # If we have a possible python declaration
        # use jedi to find possible declarations.
        found = self.attempt_get_definition(script)
        if not found:
            found = self.attempt_go_to(script)

    def attempt_go_to(self, script):
        """ Uses `jedi.api.Script` goto function
            for possible definition.

            :param script: `jedi.api.Script` object

            :return: bool
        """
        found = script.goto()
        if len(found) > 0:
            if len(found) == 1:
                x = found[0]
                self._jump_to_in_window(x.module_path, x.start_pos[0], x.start_pos[1])

            else:
                self._window_quick_panel_open_window(found)
                return True

        return False


    def attempt_get_definition(self, script):
        """ Uses `jedi.api.Script` get_definition function
            for possible definition.

            :param script: `jedi.api.Script` object

            :return: bool
        """
        found = script.get_definition()
        if len(found) == 1:
            x = found[0]
            self._jump_to_in_window(x.module_path, x.start_pos[0], x.start_pos[1])
            return True
        elif len(found) > 1:
            self._window_quick_panel_open_window(found)
            return True

        return False


    def _jump_to_in_window(self, filename, line_number=None, column_number=None):
        """ Opens a new window and jumps to declaration if possible

            :param filename: string or int
            :param line_number: int
            :param column_number: int
        """
        active_window = self.view.window()

        # If the file was selected from a drop down list
        if isinstance(filename, int):
            filename = self.options[filename]
            line_number, column_number = self.options_map[filename]

        active_window.open_file('%s:%s:%s' % (filename, line_number or 0, column_number or 0), sublime.ENCODED_POSITION)


    def _window_quick_panel_open_window(self, options):
        """ Shows the active `sublime.Window` quickpanel (dropdown) for
            user selection.

            :param option: list of `jedi.api_classes.Definition`
        """

        active_window = self.view.window()

        # Get the filenames
        self.options = [o.module_path for o in options]

        # Map the filenames to line and column numbers
        self.options_map = dict((o.module_path, (o.start_pos[0], o.start_pos[1])) for o in options)

        # Show the user a selection of filenames
        active_window.show_quick_panel(self.options, self._jump_to_in_window)
