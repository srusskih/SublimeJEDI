# -*- coding: utf-8 -*-
import functools

import sublime
import sublime_plugin

from .utils import is_python_scope, ask_daemon, get_settings
from .console_logging import getLogger
from .settings import get_settings_param

logger = getLogger(__name__)
FOLLOWING_CHARS = set(["\r", "\n", "\t", " ", ")", "]", ";", "}", "\x00"])


class SublimeJediParamsAutocomplete(sublime_plugin.TextCommand):
    """
    Function / Class constructor autocompletion command
    """
    def run(self, edit, characters='('):
        """
        Insert completion character, and complete function parameters
        if possible

        :param edit: sublime.Edit
        :param characters: str
        """
        self._insert_characters(edit, characters, ')')

        # Deprecated: scope should be tested in key bindings
        #
        # nothing to do with non-python code
        # if not is_python_scope(self.view, self.view.sel()[0].begin()):
        #     logger.info('no function args completion in strings')
        #     return

        if get_settings(self.view)['complete_funcargs']:
            ask_daemon(self.view, self.show_template, 'funcargs', self.view.sel()[0].end())

    @property
    def auto_match_enabled(self):
        """ check if sublime closes parenthesis automaticly """
        return self.view.settings().get('auto_match_enabled', True)

    def _insert_characters(self, edit, open_pair, close_pair):
        """
        Insert autocomplete character with closed pair
        and update selection regions

        If sublime option `auto_match_enabled` turned on, next behavior have to be:

            when none selection

            `( => (<caret>)`
            `<caret>1 => ( => (<caret>1`

            when text selected

            `text => (text<caret>)`

        In other case:

            when none selection

            `( => (<caret>`

            when text selected

            `text => (<caret>`


        :param edit: sublime.Edit
        :param characters: str
        """
        regions = [a for a in self.view.sel()]
        self.view.sel().clear()

        for region in reversed(regions):

            next_char = self.view.substr(region.begin())
            # replace null byte to prevent error
            next_char = next_char.replace('\x00', '\n')
            logger.debug("Next characters: {0}".format(next_char))

            following_text = next_char not in FOLLOWING_CHARS
            logger.debug("Following text: {0}".format(following_text))

            if self.auto_match_enabled:
                self.view.insert(edit, region.begin(), open_pair)
                position = region.end() + 1

                # IF selection is non-zero
                # OR after cursor no any text and selection size is zero
                # THEN insert closing pair
                if region.size() > 0 or not following_text and region.size() == 0:
                    self.view.insert(edit, region.end() + 1, close_pair)
                    position += (len(open_pair) - 1)
            else:
                self.view.replace(edit, region, open_pair)
                position = region.begin() + len(open_pair)

            self.view.sel().add(sublime.Region(position, position))

    def show_template(self, view, template):
        view.run_command('insert_snippet', {"contents": template})


class Autocomplete(sublime_plugin.EventListener):
    """
    Sublime Text autocompletion integration
    """

    completions = []
    cplns_ready = None
    cplns_mode = None

    def on_load(self, view):
        self.cplns_mode = get_settings_param(
            view,
            'sublime_completions_visibility',
            default='default'
        )

    def on_query_completions(self, view, prefix, locations):
        """ Sublime autocomplete event handler

        Get completions depends on current cursor position and return
        them as list of ('possible completion', 'completion type')

        :param view: `sublime.View` object
        :type view: sublime.View
        :param prefix: string for completions
        :type prefix: basestring
        :param locations: offset from beginning
        :type locations: int

        :return: list of tuple(str, str)
        """
        logger.info('JEDI completion triggered')

        if self.cplns_ready:
            logger.debug(
                'JEDI has completion in daemon response {0}'.format(
                    self.completions
                )
            )

            self.cplns_ready = None
            if self.completions:
                cplns, self.completions = self.completions, []
                if self.cplns_mode in ('default', 'jedi'):
                    return (
                        [tuple(i) for i in cplns],
                        sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
                    )
                return [tuple(i) for i in cplns]
            return

        if view.settings().get("repl", False):
            logger.debug("JEDI does not complete in SublimeREPL views")
            return

        # nothing to do with non-python code
        if not is_python_scope(view, locations[0]):
            logger.debug('JEDI does not complete in strings')
            return

        # get completions list
        if self.cplns_ready is None:
            ask_daemon(view, self.show_completions, 'autocomplete', locations[0])
            self.cplns_ready = False
        if self.cplns_mode == 'jedi':
            view.run_command("hide_auto_complete")
        return

    def show_completions(self, view, completions):
        # XXX check position
        self.cplns_ready = True
        if completions:
            self.completions = completions
            view.run_command("hide_auto_complete")
            sublime.set_timeout(functools.partial(self.show, view), 0)

    def show(self, view):
        logger.debug("command history: " + str([
            view.command_history(-1),
            view.command_history(0),
            view.command_history(1),
        ]))
        command = view.command_history(0)

        # if completion was triggerd by tab, then hide "tab" or "snippet"
        if command[0] == 'insert_best_completion' or\
                (command == (u'insert', {'characters': u'\t'}, 1)):
            view.run_command('undo')

        view.run_command("auto_complete", {
            'disable_auto_insert': True,
            'api_completions_only': False,
            'next_completion_if_showing': False,
            'auto_complete_commit_on_tab': True,
        })
