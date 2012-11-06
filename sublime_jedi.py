import sublime
import sublime_plugin
import os.path
import re
import traceback

try:
    import jedi
except ImportError:
    import sys
    import os
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
