import sublime, sublime_plugin
from .utils import PythonCommandMixin, is_python_scope
from .settings import get_plugin_settings


class PySelectEventListener(sublime_plugin.EventListener):

    def show_py(self, view) -> None:
        '''
        Show the Python Interpreter used by SublimeJEDI on statusbar
        '''
        if is_python_scope(view, view.sel()[0].begin()):
            view.window().status_message('   Py: {}'.format(get_plugin_settings().get('python_interpreter')))

    def on_load(self, view) -> None:
        self.show_py(view)

    def on_activated(self, view) -> None:
        self.show_py(view)


class ListAvaliablePython(sublime_plugin.ListInputHandler):
    def __init__(self, view):
        self.view = view

    def list_items(self):
        return get_plugin_settings().get('python_interpreters')

    def confirm(self, sel_py):
        get_plugin_settings().set('python_interpreter', sel_py)
        sublime.save_settings('sublime_jedi.sublime-settings')


class SublimeJediPySelect(PythonCommandMixin, sublime_plugin.TextCommand):
    '''
    Select Python Interpreter
    '''

    def run(self, edit, list_avaliable_python):
        # list_avaliable_python: the selected python
        pass

    def input(self, args):
        return ListAvaliablePython(self.view)
