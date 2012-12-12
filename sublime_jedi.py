import sublime
import sublime_plugin
import os.path
import re
import traceback
import sys
import os

os.environ['VIRTUAL_ENV'] = '/home/jonathan/workspace/virtualenvs/gradcon4/'
sys.path.append('/home/jonathan/workspace/virtualenvs/gradcon4/lib/python2.7/site-packages/')

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

class PythonGoTo(sublime_plugin.TextCommand):

    def run(self, edit):

        script = get_script(self.view, self.view.sel()[0].begin())

        # Not sure if this is the right way around?
        found = self.attempt_get_definition(script)
        if not found:
            found = self.attempt_go_to(script)

            if not found:
                self.view.run_command('string_go_to')

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


FOUND_PATHS_CACHE = {}


class StringGoTo(sublime_plugin.TextCommand):
    """
    Is useful in Django when we are trying to jump from template to template.
    Gets the string, and attemps to open a filename associated with it.
    """

    known_file_types = (
        'xml', 'html', 'py', 'js',
    )

    def run(self, edit):

        # Get the selected region
        sels = self.view.sel()
        region = self.view.word(sels[0])

        self.file_type = self._get_file_type(self.view.file_name())

        string = self.get_string(region)
        if string:
            self.string_dispatch(string)



    def get_string(self, region):
        possible_string_end = self.check_if_string(region.a)
        if possible_string_end is None:
            return False

        possible_string_start = self.check_if_string(region.a-1, True)
        if possible_string_start is None:
            return False

        return possible_string_start + possible_string_end

    def check_if_string(self, starting, reverse=False):
        # Has got to be a cleaner/better way to do this
        char = None
        counter = starting
        possible_filename = ''
        found_string_declaration = False
        while True:
            char = self.view.substr(counter)

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


    def string_dispatch(self, string):
        possible_filename = string

        found = FOUND_PATHS_CACHE.get(possible_filename)
        if found:
            self.possible_files = [found]
            self.open_file_in_active_window(0)
            return


        filename_parts = possible_filename.split('.')
        if len(filename_parts) == 1:
            return

        if filename_parts[-1] not in self.known_file_types:
            # employers.urls -> employer/urls.py
            possible_filename = '%s.%s' % ('/'.join(filename_parts), self.file_type)

        self.possible_files = self.get_files(possible_filename)

        active_window = self.view.window()


        if len(self.possible_files) > 1:
            active_window.show_quick_panel(self.possible_files, self.open_file_in_active_window)

        elif len(self.possible_files) == 1:
            FOUND_PATHS_CACHE[possible_filename] = self.possible_files[0]
            self.open_file_in_active_window(0)

    def open_file_in_active_window(self, picked):
        if picked == -1:
            return
        active_window = self.view.window()
        active_window.open_file(self.possible_files[picked])


    def get_files(self, possible_filename):
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






