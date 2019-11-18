import sublime, sublime_plugin
from .utils import PythonCommandMixin, is_python_scope
from .settings import get_plugin_settings, get_settings_param


class PySelectEventListener(sublime_plugin.EventListener):

    def show_py(self, view) -> None:
        '''
        Show the Python Interpreter used by SublimeJEDI on statusbar
        '''
        cur_py = get_settings_param(view, 'python_interpreter')

        if is_python_scope(view, view.sel()[0].begin()) and cur_py:
            view.window().status_message('   Py: {}'.format(cur_py))

    def on_load(self, view) -> None:
        self.show_py(view)

    def on_activated(self, view) -> None:
        self.show_py(view)


class ListAvaliablePython(sublime_plugin.ListInputHandler):
    def __init__(self, view):
        self.view = view

    def list_items(self):
        all_py = get_plugin_settings().get('python_interpreters')

        return all_py if all_py else []

    def confirm(self, sel_py):
        if sel_py:
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
