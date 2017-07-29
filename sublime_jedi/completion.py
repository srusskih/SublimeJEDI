# -*- coding: utf-8 -*-
import functools

import sublime
import sublime_plugin

from .utils import (ask_daemon,
                    get_settings,
                    is_python_scope,
                    is_repl,
                    is_sublime_v2)
from .console_logging import getLogger
from .settings import get_settings_param

logger = getLogger(__name__)
FOLLOWING_CHARS = set(["\r", "\n", "\t", " ", ")", "]", ";", "}", "\x00"])
PLUGIN_ONLY_COMPLETION = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS


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
    is_completion_ready = None

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
        if is_repl(view):
            logger.debug("JEDI does not complete in SublimeREPL views")
            return

        if not is_python_scope(view, locations[0]):
            logger.debug('JEDI completes only in python scope')
            return

        logger.info('JEDI completion triggered')

        completion_mode = self._get_completion_mode(view)

        if self.is_completion_ready:
            logger.debug(
                'JEDI has completion in daemon response {0}'.format(
                    self.completions
                )
            )

            self.is_completion_ready = None

            if self.completions:
                # sort completions by frequency in document
                buffer = view.substr(sublime.Region(0, view.size()))
                cplns = sorted(
                    self.completions,
                    key=lambda x: (
                        -buffer.count(x[1]),  # frequency in the text
                        len(x[1]) - len(x[1].strip('_')),  # how many undescores
                        x[1]  # alphabetically
                    )
                )
                cplns = [tuple(x) for x in cplns]
                self.completions = []
                if completion_mode in ('default', 'jedi'):
                    return cplns, PLUGIN_ONLY_COMPLETION
                return cplns

            return

        if self.is_completion_ready is None:
            if completion_mode == 'all':
                self.completions = self._get_default_completions(view, prefix, locations[0])

            ask_daemon(view, self._show_completions, 'autocomplete', locations[0])
            self.is_completion_ready = False

        view.run_command("hide_auto_complete")
        return

    def _get_default_completions(self, view, prefix, location):
        """
        Returns default sublime completion for current prefix
        """
        default_completions = list(set([
            (completion + "\tDefault", completion)
            for completion in list(view.extract_completions(prefix, location))
            if len(completion) > 3
        ]))

        return default_completions

    def _show_completions(self, view, completions):
        """
        TODO: check position
        """
        self.is_completion_ready = True

        if completions:
            self.completions = completions + self.completions

        if self.completions:
            view.run_command("hide_auto_complete")
            sublime.set_timeout(functools.partial(self._show_popup, view), 0)

    def _show_popup(self, view):
        """
        Show completion Pop-Up
        """
        if is_sublime_v2():
           self._fix_sublime2_tab_completion_issue(view)

        self._fix_tab_completion_issue(view)

        view.run_command("auto_complete", {
            'disable_auto_insert': True,
            'api_completions_only': False,
            'next_completion_if_showing': False,
            'auto_complete_commit_on_tab': True,
        })

    def _fix_sublime2_tab_completion_issue(self, view):
        """Fix ST2 issue with tab completion & commit on tab."""
        logger.debug("command history: " + str([
            view.command_history(-1),
            view.command_history(0),
            view.command_history(1),
        ]))
        last_command = view.command_history(0)

        # when you type "os.<tab>" originaly it will insert `self.` snippet
        # this detects such behavior and trying avoid it.
        if (last_command[0] == 'insert_best_completion'):
            view.run_command('undo')

    def _fix_tab_completion_issue(self, view):
        """Fix issue with tab completion & commit on tab."""
        logger.debug("command history: " + str([
            view.command_history(-1),
            view.command_history(0),
            view.command_history(1),
        ]))
        last_command = view.command_history(0)

        # when you hit <tab> after completion commit, completion popup
        # will appeares and `\t` would be inserted
        # this detecs such behavior and trying avoid it.
        if last_command == (u'insert', {'characters': u'\t'}, 1):
            view.run_command('undo')

    def _get_completion_mode(self, view):
        return get_settings_param(view, 'sublime_completions_visibility',
                                  'default')
