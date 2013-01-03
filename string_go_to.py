import sublime
import sublime_plugin
import os.path
import re
import sys
import os

from sublime_jedi import JediEnvMixin

FOUND_PATHS_CACHE = {}

python_function_pattern = 'def %s'
python_class_pattern = 'class %s'
python_variable_pattern = '%s.*='

python_definition_patterns = (
    python_function_pattern,
    python_class_pattern,
    python_variable_pattern,
)


def get_string(view):
    sels = view.sel()
    region = view.word(sels[0])
    possible_string_end = _get_string(view, region.a)
    if possible_string_end is None:
        return False

    possible_string_start = _get_string(view, region.a-1, True)
    if possible_string_start is None:
        return False

    return possible_string_start + possible_string_end

def _get_string(view, starting, reverse=False):
    # Has got to be a cleaner/better way to do this
    char = None
    counter = starting
    possible_filename = ''
    found_string_declaration = False
    while True:
        char = view.substr(counter)

        if char == '\n':
            break

        if char == "\'" or char == '\"':
            found_string_declaration = True
            break

        possible_filename += char

        if not reverse:
            counter += 1
        else:
            counter -= 1

    if reverse:
        possible_filename = possible_filename[::-1]

    return possible_filename if found_string_declaration else None

class StringGoTo(JediEnvMixin, sublime_plugin.TextCommand):
    """
    Is useful in Django when we are trying to jump from template to template.
    Gets the string, and attemps to open a filename associated with it.
    """

    known_file_types = (
        'xml', 'html', 'py', 'js',
    )

    def run(self, edit):

        # install user env
        self.install_env()

        self.file_type = self._get_file_type(self.view.file_name())

        string = get_string(self.view)
        if string:
            self.string_dispatch(string)


    def string_dispatch(self, string):
        possible_filename = string

        # Return cached results if exist
        found = FOUND_PATHS_CACHE.get(possible_filename)
        if found:
            self.possible_files = [found]
            self.open_file_in_active_window(0)
            return


        filename_parts = possible_filename.split('.')
        if len(filename_parts) == 1:
            return

        if filename_parts[-1] not in self.known_file_types:
            # employers.views -> employer/views.py
            # employer.views.function_in_view -> employer/views.py GOTO function_in_view
            possible_filename = '%s.%s' % ('/'.join(filename_parts), self.file_type)
            test_string = 'test.test_string_open.hello_world'
            # Possibly make this recursive or loop?
            # Not needed for my django development atm.
            if not self.get_and_open_possible_file(possible_filename):

                # Can't handle anything but python files atm.
                if self.file_type != 'py':
                    return

                possible_filename = '%s.%s' % ('/'.join(filename_parts[:-1]), self.file_type)
                found = self.get_files(possible_filename)
                possible_definition = filename_parts[-1]
                print 'searching for %s -> %s' % (possible_filename, possible_definition)
                if found:
                    print 'found'
                    if len(found) == 1:
                        self.go_to_in_new_window(found[0], possible_definition)

                    elif len(found) > 1:
                        active_window = self.view.window()
                        self.options = found
                        self.possible_definition = possible_definition
                        active_window.show_quick_panel(self.options, lambda x: self.go_to_in_new_window(self.options[x] if x != -1 else None, possible_definition))
        else:
            self.get_and_open_possible_file(possible_filename)


    def go_to_in_new_window(self, filepath, possible_definition):
        """
        Look for possible python declaration, if found open in a
        new window, and take the cursor the the declaration.
        """
        if not filepath:
            return

        found_definitions = []

        src = open(filepath).read()
        smallest_column = 100
        smallest_column_pos = None
        for pattern in python_definition_patterns:
            for match in re.finditer(pattern % possible_definition, src):
                if match:
                    start = match.start()
                    line_num = src.count('\n', 0, start) + 1
                    column_num = start - src.rfind('\n', 0, start)

                    if column_num < smallest_column:
                        smallest_column = column_num
                        smallest_column_pos = len(found_definitions)

                    found_definitions.append((column_num, line_num))


        if found_definitions:
            col, line = found_definitions[smallest_column_pos]
            self.jump_to_in_window(filepath, line, col)


    def jump_to_in_window(self, filename, line_number=None, column_number=None):
        active_window = self.view.window()

        # If the file was selected from a drop down list
        if isinstance(filename, int):
            filename = self.options[filename]
            line_number, column_number = self.options_map[filename]

        active_window.open_file('%s:%s:%s' % (filename, line_number or 0, column_number or 0), sublime.ENCODED_POSITION)

    def get_and_open_possible_file(self, possible_filename):
        self.possible_files = self.get_files(possible_filename)

        active_window = self.view.window()


        if len(self.possible_files) > 1:
            active_window.show_quick_panel(self.possible_files, self.open_file_in_active_window)
            return True

        elif len(self.possible_files) == 1:
            # Cache filename -> filepath if we found only one result
            FOUND_PATHS_CACHE[possible_filename] = self.possible_files[0]
            self.open_file_in_active_window(0)
            return True

        return False

    def open_file_in_active_window(self, picked):
        if picked == -1:
            return
        active_window = self.view.window()
        active_window.open_file(self.possible_files[picked])

    CACHED_FILEPATHS = None
    def cache_file_paths(self):
        # TODO: Add some possible indexing on filepaths?
        self.CACHED_FILEPATHS = set()
        for path in sys.path + self.view.window().folders():
            for root, dirs, files in os.walk(path): # Walk directory tree

                if root.startswith('./'):
                    continue

                for f in files:
                    self.CACHED_FILEPATHS.add('%s/%s' % (root, f))

    def get_files(self, possible_filename):

        if self.CACHED_FILEPATHS is None:
            self.cache_file_paths()

        possible_files = []
        for filepath in self.CACHED_FILEPATHS:
            if re.search('%s$' % possible_filename, filepath):
                # if possible_filename in full_path:
                possible_files.append(filepath)
        return possible_files

    def _get_file_type(self, filename):
        return filename.split('.')[-1]
