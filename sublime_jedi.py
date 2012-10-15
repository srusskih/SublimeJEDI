import sublime
import sublime_plugin
import jedi

class SublimeJedi(sublime_plugin.TextCommand):
    our_jedi = jedi.Script()