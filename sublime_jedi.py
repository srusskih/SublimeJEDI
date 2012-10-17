import sublime
import sublime_plugin


try:
    import jedi
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.getcwd(), 'jedi'))
    import jedi


def get_script(view, location):
    """ `jedi.Script` fabric

        **view** - sublime.View object
        **location** - offset from beginning

        Returns: `jedi.api.Script` object
    """
    text = view.substr(sublime.Region(0, view.size()))
    source_path = view.file_name()
    (current_line, current_column) = view.rowcol(location)
    return jedi.Script(text, current_line, current_column, source_path)


class Autocomplete(sublime_plugin.EventListener):
    def proposal_string(self, complete):
        """ Returns string that would be visiable in the completion dialog

            **complete** is `jedi.api.Complete` object

            Returns: string
        """
        output = [complete.word, '\t',  complete.description]
        return ''.join(output)

    def on_query_completions(self, view, prefix, locations):
        script = get_script(view, locations[0])
        completions = [(self.proposal_string(complete), complete.word)
            for complete in script.complete()]
        return completions
