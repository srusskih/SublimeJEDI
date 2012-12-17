import sublime
import sublime_plugin
import os.path
import re
import traceback
import sys
import os

try:
    import jedi
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jedi'))
    import jedi

_dotcomplete = []

def get_script(view, location):
    """ `jedi.Script` fabric

        **view** - sublime.View object
        **location** - offset from beginning

        Returns: `jedi.api.Script` object
    """
    text = view.substr(sublime.Region(0, view.size()))
    source_path = view.file_name()
    (current_line, current_column) = view.rowcol(location)
    return jedi.Script(text.encode("utf-8"), current_line+1, current_column, source_path.encode("utf-8"))

language_regex = re.compile("(?<=source\.)[\w+#]+")


def get_language(view):
    caret = view.sel()[0].a
    language = language_regex.search(view.scope_name(caret))
    if language == None:
        return None
    return language.group(0)


def format(complete):
    """ Returns a tuple of the string that would be visible in the completion dialogue,
        and the snippet to insert for the completion

        **complete** is `jedi.api.Complete` object

        Returns: tuple(string, string)
    """
    root = complete.name
    display, insert = complete.word, complete.word
    p = None
    while isinstance(root, jedi.evaluate.ArrayElement):
        root = root.parent()

    if isinstance(root, jedi.keywords.Keyword):
        display += "\tkeyword"
    else:
        p = root.get_parent_until(
            [
                jedi.parsing.Import,
                jedi.parsing.Statement,
                jedi.parsing.Class,
                jedi.parsing.Function, jedi.evaluate.Function
            ])

    if p:
        if p.isinstance(jedi.parsing.Function) or p.isinstance(jedi.evaluate.Function):
            try:
                cls = root.get_parent_until([jedi.evaluate.Instance])
                params = list(p.params)
                def safe_name(name, idx):
                    try:
                        name = a.get_name().get_code()
                    except:
                        name = "unknown_varname%d" % idx
                    return name
                params = [safe_name(a, idx) for idx, a in enumerate(params)]
                if cls.isinstance(jedi.evaluate.Instance):
                    # Remove "self"
                    try:
                        params.remove(cls.get_func_self_name(p))
                    except:
                        pass
                paramstr = ", ".join(params)
            except:
                traceback.print_exc()
                params = []
                paramstr = ""

            display = "%s(%s)" % (p.name, paramstr)
            insert = "%s(" % p.name
            num = 1
            for par in params:
                if num > 1:
                    insert += ", "
                insert += "${%d:%s}" % (num, par)
                num += 1
            insert += ")"
            display += "\tdef"
        elif p.isinstance(jedi.parsing.Statement):
            display +=  "\tvariable"
        elif p.isinstance(jedi.parsing.Import):
            display += "\tmodule"
        elif p.isinstance(jedi.parsing.Class):
            display += "\tclass"
    return (display, insert)


class SublimeJediComplete(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            self.view.insert(edit, region.end(), ".")

        # Hack to redisplay the completion dialog with new information
        # if it was already showing

        self.view.run_command("hide_auto_complete")
        sublime.set_timeout(self.delayed_complete, 1)

    def delayed_complete(self):
        global _dotcomplete
        script = get_script(self.view, self.view.sel()[0].begin())
        _dotcomplete = script.complete()
        if len(_dotcomplete):
            # Only complete if there's something to complete
            self.view.run_command("auto_complete")

class Autocomplete(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):
        global _dotcomplete
        if get_language(view) != "python":
            return None
        if len(_dotcomplete) > 0:
            completions = _dotcomplete
        else:
            script = get_script(view, locations[0])
            completions = script.complete()
        _dotcomplete = []
        completions = [format(complete) for complete in completions]
        return completions


# Have we added our site-packages to sys.path
added_to_path = False

class PythonGoTo(sublime_plugin.TextCommand):

    def run(self, edit):
        global added_to_path

        # If we have a string, dispatch it elsewhere
        if get_string(self.view):
            self.view.run_command('string_go_to')
            return

        if not added_to_path:
            sys.path.append('/home/jonathan/workspace/virtualenvs/gradcon4/lib/python2.7/site-packages/')
            added_to_path = True

        script = get_script(self.view, self.view.sel()[0].begin())

        # Not sure if this is the right way around?
        found = self.attempt_get_definition(script)
        if not found:
            found = self.attempt_go_to(script)

    def attempt_go_to(self, script):
        found = script.goto()
        if len(found) > 0:
            if len(found) == 1:
                x = found[0]
                self.jump_to_in_window(x.module_path, x.start_pos[0], x.start_pos[1])

            else:
                self.window_quick_panel_open_window(found)
                return True

        return False


    def attempt_get_definition(self, script):
        found = script.get_definition()
        if len(found) == 1:
            x = found[0]
            self.jump_to_in_window(x.module_path, x.start_pos[0], x.start_pos[1])
            return True
        elif len(found) > 1:
            self.window_quick_panel_open_window(found)
            return True

        return False


    def jump_to_in_window(self, filename, line_number=None, column_number=None):
        active_window = self.view.window()

        # If the file was selected from a drop down list
        if isinstance(filename, int):
            filename = self.options[filename]
            line_number, column_number = self.options_map[filename]

        active_window.open_file('%s:%s:%s' % (filename, line_number or 0, column_number or 0), sublime.ENCODED_POSITION)


    def window_quick_panel_open_window(self, options):
        """
        Assumes the options is a list of jedi.api_classed.Definition
        """
        # TODO: Maybe handle multiple?

        active_window = self.view.window()
        self.options = [o.module_path for o in options]
        self.options_map = dict((o.module_path, (o.start_pos[0], o.start_pos[1])) for o in options)
        active_window.show_quick_panel(self.options, self.jump_to_in_window)


def get_string(view):
    sels = view.sel()
    region = view.word(sels[0])
    possible_string_end = check_if_string(view, region.a)
    if possible_string_end is None:
        return False

    possible_string_start = check_if_string(view, region.a-1, True)
    if possible_string_start is None:
        return False

    return possible_string_start + possible_string_end

def check_if_string(view, starting, reverse=False):
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

FOUND_PATHS_CACHE = {}

python_function_pattern = 'def %s'
python_class_pattern = 'class %s'
python_variable_pattern = '%s.*='

python_definition_patterns = (
    python_function_pattern,
    python_class_pattern,
    python_variable_pattern,
)

class StringGoTo(sublime_plugin.TextCommand):
    """
    Is useful in Django when we are trying to jump from template to template.
    Gets the string, and attemps to open a filename associated with it.
    """

    known_file_types = (
        'xml', 'html', 'py', 'js',
    )

    def run(self, edit):

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
            # test_string = 'test.test_string_open.hello_world'
            # Possibly make this recursive or loop?
            # Not needed for my django development atm.
            if not self.get_and_open_possible_file(possible_filename):

                # Can't handle anything but python files atm.
                if self.file_type != 'py':
                    return

                possible_filename = '%s.%s' % ('/'.join(filename_parts[:-1]), self.file_type)
                found = self.get_files(possible_filename)
                possible_definition = filename_parts[-1]
                if found:
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
        if not filepath:
            print 'no file'
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


    def get_files(self, possible_filename):
        # Not sure whether to cache all possible filenames?
        possible_files = []
        for path in self.view.window().folders():
            for root, dirs, files in os.walk(path): # Walk directory tree
                for f in files:
                    full_path = '%s/%s' % (root, f)
                    if re.search('%s$' % possible_filename, full_path):
                        # if possible_filename in full_path:
                        possible_files.append(full_path)
        return possible_files

    def _get_file_type(self, filename):
        return filename.split('.')[-1]






