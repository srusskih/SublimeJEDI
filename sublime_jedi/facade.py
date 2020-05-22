# -*- coding: utf-8 -*-
from itertools import chain
from operator import itemgetter

import jedi
from jedi.api.completion import Parameter

from .console_logging import getLogger
from .utils import unique

logger = getLogger(__name__)


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
        project,
        complete_funcargs,
        source,
        line,
        column,
        filename=''
    ):
        filename = filename or None
        self.script = jedi.Script(
            source=source,
            path=filename,
            project=project,
        )
        self._line = line
        self._column = column
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
        )
        return ', '.join(p[1] for p in call_parameters)

    def get_autocomplete(self, *args, **kwargs):
        """Jedi completion."""
        completions = chain(
            self._complete_call_assigments(with_keywords=True),
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
        defs = self.script.infer(line=self._line, column=self._column)
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
        completions = self.script.complete(
            line=self._line,
            column=self._column,
            fuzzy=True,
        )
        for complete in completions:
            yield complete.name + '\t' + complete.type, complete.name

    def _goto(self, follow_imports):
        """Jedi "go to Definitions" functionality.

        :rtype: list of (str, int, int) or None
        """
        definitions = self.script.goto(
            line=self._line,
            column=self._column,
            follow_imports=follow_imports,
        )
        if all(d.type == 'import' for d in definitions):
            # check if it an import string and if it is get definition
            definitions = self.script.infer(
                line=self._line,
                column=self._column,
            )
        return [(i.module_path, i.line, i.column + 1)
                for i in definitions if not i.in_builtin_module()]

    def _usages(self):
        """Jedi "find usages" functionality.

        :rtype: list of (str, int, int)
        """
        usages = self.script.get_references(
            line=self._line,
            column=self._column,
        )
        return [
            (i.module_path, i.line, i.column + 1)
            for i in usages if not i.in_builtin_module()
        ]

    def _complete_call_assigments(self, with_keywords=True):
        """Get function or class parameters and build Sublime Snippet string
        for completion

        :rtype: str
        """
        try:
            call_definition = self.script.get_signatures(
                line=self._line,
                column=self._column,
            )[0]
        except IndexError:
            # probably not a function/class call
            return

        yield from get_function_parameters(call_definition, with_keywords)


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

    yield from format_function_parameters(params)


def format_function_parameters(parameters):
    for index, (name, value) in enumerate(parameters, 1):
        if value is not None:
            yield (name + '\tparam', '%s=${%d:%s}' % (name, index, value))
        else:
            yield (name + '\tparam', '${%d:%s}' % (index, name))
