# -*- coding: utf-8 -*-
from itertools import chain
from operator import itemgetter

import jedi
from jedi.api.completion import Parameter

from .console_logging import getLogger
from .utils import unique

logger = getLogger(__name__)


def format_completion(complete):
    """Returns a tuple of the string that would be visible in
    the completion dialogue and the completion word

    :type complete: jedi.api_classes.Completion
    :rtype: (str, str)
    """
    display, insert = complete.name + '\t' + complete.type, complete.name
    return display, insert


def get_function_parameters(call_signature, with_keywords=True):
    """Return list function parameters, prepared for sublime completion.

    Tuple contains parameter name and default value

    Parameters list excludes: self, *args and **kwargs parameters

    :type call_signature: jedi.api.classes.CallSignature
    :rtype: list of (str, str or None)
    """
    if not call_signature:
        return []

    params = []
    for param in call_signature.params:
        logger.debug('Parameter: {0}'.format((
            type(param._name),
            param._name.get_kind(),
            param._name.string_name,
            param.description,
        )))

        # print call sign looks like: "value, ..., sep, end, file, flush"
        # and all params after '...' are non required and not a keywords
        if not with_keywords and param.name == '...':
            break

        if (not param.name or
                param.name in ('self', '...') or
                param._name.get_kind() == Parameter.VAR_POSITIONAL or
                param._name.get_kind() == Parameter.VAR_KEYWORD):
            continue

        param_description = param.description.replace('param ', '')
        is_keyword = '=' in param_description

        if is_keyword and with_keywords:
            default_value = param_description.rsplit('=', 1)[1].lstrip()
            params.append((param.name, default_value))
        elif is_keyword and not with_keywords:
            continue
        else:
            params.append((param.name, None))

    return params


class JediFacade:
    """Facade to call Jedi API.


     Action       | Method
    ===============================
     autocomplete | get_autocomplete
    -------------------------------
     goto         | get_goto
    -------------------------------
     usages       | get_usages
    -------------------------------
     funcargs     | get_funcargs
    --------------------------------
    """
    def __init__(
            self,
            env,
            complete_funcargs,
            source,
            line,
            column,
            filename='',
            encoding='utf-8',
            sys_path=None):
        filename = filename or None
        self.script = jedi.Script(
            source=source,
            line=line,
            column=column,
            path=filename,
            encoding=encoding,
            environment=env,
            sys_path=sys_path,
        )
        self.auto_complete_function_params = complete_funcargs

    def get(self, _action, *args, **kwargs):
        """Action dispatcher."""
        try:
            return getattr(self, 'get_' + _action)(*args, **kwargs)
        except Exception:
            logger.exception('`JediFacade.get_{0}` failed'.format(_action))

    def get_goto(self, follow_imports=True):
        """ Jedi "Go To Definition" """
        return self._goto(follow_imports=follow_imports)

    def get_usages(self, *args, **kwargs):
        """ Jedi "Find Usage" """
        return self._usages()

    def get_funcargs(self, *args, **kwargs):
        """Complete callable object parameters with Jedi."""
        complete_all = self.auto_complete_function_params == 'all'
        call_parameters = self._complete_call_assigments(
            with_keywords=complete_all,
            with_values=complete_all
        )
        return ', '.join(p[1] for p in call_parameters)

    def get_autocomplete(self, *args, **kwargs):
        """Jedi completion."""
        completions = chain(
            self._complete_call_assigments(with_keywords=True,
                                           with_values=False),
            self._completion()
        )
        return list(unique(completions, itemgetter(0)))

    def get_docstring(self, *args, **kwargs):
        return self._docstring()

    def get_signature(self, *args, **kwargs):
        return self._docstring(signature=1)

    def _docstring(self, signature=0):
        """ Jedi show doctring or signature

        :rtype: str
        """
        defs = self.script.goto_definitions()
        assert isinstance(defs, list)

        if len(defs) > 0:
            if signature:
                calltip_signature = defs[0].docstring().split('\n\n')[0]
                return calltip_signature.replace('\n', ' ').replace(' = ', '=')
            else:
                return defs[0].docstring()

    def _completion(self):
        """Regular completions.

        :rtype: list of (str, str)
        """
        completions = self.script.completions()
        for complete in completions:
            yield format_completion(complete)

    def _goto(self, follow_imports):
        """Jedi "go to Definitions" functionality.

        :rtype: list of (str, int, int) or None
        """
        definitions = self.script.goto_assignments(
            follow_imports=follow_imports
        )
        if all(d.type == 'import' for d in definitions):
            # check if it an import string and if it is get definition
            definitions = self.script.goto_definitions()
        return [(i.module_path, i.line, i.column + 1)
                for i in definitions if not i.in_builtin_module()]

    def _usages(self):
        """Jedi "find usages" functionality.

        :rtype: list of (str, int, int)
        """
        usages = self.script.usages()
        return [(i.module_path, i.line, i.column + 1)
                for i in usages if not i.in_builtin_module()]

    def _complete_call_assigments(
            self,
            with_keywords=True,
            with_values=True):
        """Get function or class parameters and build Sublime Snippet string
        for completion

        :rtype: str
        """
        try:
            call_definition = self.script.call_signatures()[0]
        except IndexError:
            # probably not a function/class call
            return

        parameters = get_function_parameters(call_definition, with_keywords)
        for index, parameter in enumerate(parameters):
            name, value = parameter

            if value is not None and with_values:
                yield (name + '\tparam',
                       '%s=${%d:%s}' % (name, index + 1, value))
            else:
                yield (name + '\tparam',
                       '${%d:%s}' % (index + 1, name))
