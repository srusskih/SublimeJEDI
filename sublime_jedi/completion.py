# -*- coding: utf-8 -*-
import re
from threading import Timer

import sublime
import sublime_plugin

from .console_logging import getLogger
from .daemon import ask_daemon
from .utils import get_settings, is_python_scope, is_repl


logger = getLogger(__name__)
FOLLOWING_CHARS = {"\r", "\n", "\t", " ", ")", "]", ";", "}", "\x00"}
PLUGIN_ONLY_COMPLETION = (
    sublime.INHIBIT_WORD_COMPLETIONS |
    sublime.INHIBIT_EXPLICIT_COMPLETIONS
)


def debounce(wait):
    """ Decorator that will postpone a functions
        execution until after wait seconds
        have elapsed since the last time it was invoked. """
    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)
            try:
                debounced.t.cancel()
            except(AttributeError):
                pass
            debounced.t = Timer(wait, call_it)
            debounced.t.start()
        return debounced
    return decorator


@debounce(0.2)
def debounced_ask_daemon(*args, **kwargs):
    ask_daemon(*args, **kwargs)


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

    _completions = []
    _previous_completions = []
    _last_location = None

    def __enabled(self):
        settings = get_settings(self.view)

        if sublime.active_window().active_view().id() != self.view.id():
            return False

        if is_repl(self.view) and not settings['enable_in_sublime_repl']:
            logger.debug("JEDI does not complete in SublimeREPL views.")
            return False

        if not is_python_scope(self.view, self.view.sel()[0].begin()):
            logger.debug('JEDI completes only in python scope.')
            return False

        return True

    def on_post_text_command(self, command, args):
        """Complete call arguments of a just committed function."""
        if command != 'commit_completion' or not self.__enabled():
            return

        location = self.view.sel()[0]

        # do not autocomplete on import lines
        line = self.view.substr(self.view.line(location)).split()
        if 'import' in line:
            return

        committed = self.view.substr(self.view.word(location))
        for display, insert in self._completions:
            if committed == insert and display.endswith('\tfunction'):
                self.view.run_command('sublime_jedi_params_autocomplete')
                break

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
        if settings['only_complete_after_regex']:
            previous_char = self.view.substr(locations[0] - 1)
            if not re.match(settings['only_complete_after_regex'], previous_char):  # noqa
                return False

        if self._last_location != locations[0]:
            self._last_location = locations[0]
            debounced_ask_daemon(
                self.view,
                self._receive_completions,
                'autocomplete',
                location=locations[0],
            )
            return [], PLUGIN_ONLY_COMPLETION

        if self._last_location == locations[0]:
            self._last_location = None
            return self._completions

    def _receive_completions(self, view, completions):
        if not completions:
            return

        logger.debug("Completions: {0}".format(completions))

        self._previous_completions = self._completions
        self._completions = completions
        if (completions and (
                not view.is_auto_complete_visible() or
                not self._is_completions_subset())):
            only_jedi_completion = (
                get_settings(self.view)['sublime_completions_visibility']
                in ('default', 'jedi')
            )
            view.run_command('hide_auto_complete')
            view.run_command('auto_complete', {
                'api_completions_only': only_jedi_completion,
                'disable_auto_insert': True,
                'next_completion_if_showing': False,
            })

    def _is_completions_subset(self):
        completions = {completion for _, completion in self._completions}
        previous = {completion for _, completion in self._previous_completions}
        return completions.issubset(previous)
