import os

import sublime
import sublime_plugin
import imp

jedi = imp.load_source('jedi', os.getcwd() + '/jedi')

def get_script(v):
    text = v.substr(sublime.Region(0, v.size()))
    source_path = v.file_name()
    if len(v.sel()) == 1:
        (current_line,current_column) = v.rowcol(v.sel()[0].begin())
    else:
        pass
    return jedi.Script(text, current_line, current_column, source_path)

class SublimeJedi(sublime_plugin.TextCommand):
    def run(self, edit):
        anakin = get_script(self.view)
        print anakin.complete()