# -*- coding: utf-8 -*-
import sublime
import sublime_plugin

from .console_logging import getLogger
from .daemon import ask_daemon, ask_daemon_with_timeout
from .utils import (get_settings,
                    is_python_scope,
                    is_repl,)

logger = getLogger(__name__)
FOLLOWING_CHARS = set(["\r", "\n", "\t", " ", ")", "]", ";", "}", "\x00"])
PLUGIN_ONLY_COMPLETION = (sublime.INHIBIT_WORD_COMPLETIONS |
                          sublime.INHIBIT_EXPLICIT_COMPLETIONS)


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
            ask_daemon(
                self.view,
                self.show_template,
                'funcargs',
                location=self.view.sel()[0].end()
            )

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


class Autocomplete(sublime_plugin.ViewEventListener):
    """Sublime Text autocompletion integration."""

    def __enabled(self):
        settings = get_settings(self.view)

        if is_repl(self.view) and not settings['enable_in_sublime_repl']:
            logger.info("JEDI does not complete in SublimeREPL views.")
            return False

        if not is_python_scope(self.view, self.view.sel()[0].begin()):
            logger.info('JEDI completes only in python scope.')
            return False

        return True

    def on_query_completions(self, prefix, locations):
        """Sublime autocomplete event handler.

        Get completions depends on current cursor position and return
        them as list of ('possible completion', 'completion type')

        :param prefix: string for completions
        :type prefix: basestring
        :param locations: offset from beginning
        :type locations: int

        :return: list of tuple(str, str)
        """
        if not self.__enabled():
            return False
        logger.info('JEDI completion triggered.')

        settings = get_settings(self.view)
        only_jedi_completion = (
            settings['sublime_completions_visibility'] in ('default', 'jedi')
        )

        cplns = ask_daemon_with_timeout(
            self.view,
            'autocomplete',
            location=locations[0]
        )
        logger.info("Completion completed.")

        cplns = [tuple(x) for x in self._sort_completions(cplns)]
        logger.debug("Completions: {0}".format(cplns))

        # disabled due to can't reproduce
        # self._fix_tab_completion_issue()

        if only_jedi_completion:
            return cplns, PLUGIN_ONLY_COMPLETION
        return cplns

    def _sort_completions(self, completions):
        """Sort completions by frequency in document."""
        buffer = self.view.substr(sublime.Region(0, self.view.size()))

        return sorted(
            completions,
            key=lambda x: (
                -buffer.count(x[1]),  # frequency in the text
                len(x[1]) - len(x[1].strip('_')),  # how many undescores
                x[1]  # alphabetically
            )
        )

    def _fix_tab_completion_issue(self):
        """Fix issue with tab completion & commit on tab.

        When you hit <tab> after completion commit,
        completion pop-up will appears
        and `\t`(tabulation) would be inserted
        the fix detects such behavior and trying avoidt.
        """
        logger.debug("command history: " + str([
            self.view.command_history(-1),
            self.view.command_history(0),
            self.view.command_history(1),
        ]))

        last_command = self.view.command_history(0)
        if last_command == (u'insert', {'characters': u'\t'}, 1):
            self.view.run_command('undo')
