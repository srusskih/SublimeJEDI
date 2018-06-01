# -*- coding: utf-8 -*-

import sys
import json
import logging

import jedi  # noqa


class JsonFormatter(logging.Formatter):
    def format(self, record):
        output = logging.Formatter.format(self, record)
        data = {
            'logging': record.levelname.lower(),
            'content': output
        }
        record = json.dumps(data)
        return record


def getLogger():
    """ Build file logger """
    log = logging.getLogger('Sublime Jedi Daemon')
    log.setLevel(logging.DEBUG)
    formatter = JsonFormatter('%(asctime)s: %(levelname)-8s: %(message)s')
    hdlr = logging.StreamHandler(sys.stderr)
    hdlr.setFormatter(formatter)
    log.addHandler(hdlr)
    return log


logger = getLogger()


def format_completion(complete):
    """ Returns a tuple of the string that would be visible in
    the completion dialogue and the completion word

    :type complete: jedi.api_classes.Completion
    :rtype: (str, str)
    """
    display, insert = complete.name + '\t' + complete.type, complete.name
    return display, insert


def get_function_parameters(call_signature, complete_all=True):
    """  Return list function parameters, prepared for sublime completion.
    Tuple contains parameter name and default value

    Parameters list excludes: self, *args and **kwargs parameters

    :type call_signature: jedi.api.classes.CallSignature
    :rtype: list of (str, str or None)
    """
    if not call_signature:
        return []

    params = []
    for param in call_signature.params:
        # when you writing a callable object
        # jedi tring to complete incompleted object
        # and returns "empty" calldefinition
        # in this case we have to skip it
        if (not complete_all and
                param.name == '...' or
                '*' in param.description):
            break

        if not param.name or param.name in ('self', '...'):
            continue

        param_description = param.description.replace('param ', '')
        if '=' in param_description:
            default_value = param_description.rsplit('=', 1)[1].lstrip()
            params.append((param.name, default_value))
        else:
            params.append((param.name, None))

    return params


class JediFacade:
    """
    Facade to call Jedi API


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
            self, env, complete_funcargs, source, line, column, filename='',
            encoding='utf-8', sys_path=None, follow_imports=False):
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
        self.follow_imports = follow_imports
        self.auto_complete_function_params = complete_funcargs
        self.is_funcargs_complete_enabled = bool(complete_funcargs)

    def get(self, _action, *args, **kwargs):
        """ Action dispatcher """
        try:
            return getattr(self, 'get_' + _action)(*args, **kwargs)
        except:
            logger.exception('`JediFacade.get_{0}` failed'.format(_action))

    def get_goto(self):
        """ Jedi "Go To Definition" """
        return self._goto()

    def get_usages(self):
        """ Jedi "Find Usage" """
        return self._usages()

    def get_funcargs(self):
        """ complete callable object parameters with Jedi """
        return self._complete_call_assigments()

    def get_autocomplete(self):
        """ Jedi "completion" """
        data = []

        try:
            data.extend(self._parameters_for_completion())
        except:
            logger.error("params completion failed")

        try:
            data.extend(self._completion() or [])
        except:
            logger.error("general completion failed")

        return data

    def get_docstring(self):
        return self._docstring()

    def get_signature(self):
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

    def _parameters_for_completion(self):
        """ Get function / class' constructor parameters completions list

        :rtype: list of str
        """
        completions = []
        try:
            in_call = self.script.call_signatures()[0]
        except IndexError:
            in_call = None

        parameters = get_function_parameters(in_call)

        for parameter in parameters:
            name, value = parameter

            if value is None:
                completions.append((name, '${1:%s}' % name))
            else:
                completions.append((name + '\t' + value,
                                   '%s=${1:%s}' % (name, value)))
        return completions

    def _completion(self):
        """ regular completions

        :rtype: list of (str, str)
        """
        completions = self.script.completions()
        return [format_completion(complete) for complete in completions]

    def _goto(self):
        """ Jedi "go to Definitions" functionality

        :rtype: list of (str, int, int) or None
        """
        definitions = self.script.goto_assignments(
            follow_imports=self.follow_imports
        )
        if all(d.type == 'import' for d in definitions):
            # check if it an import string and if it is get definition
            definitions = self.script.goto_definitions()
        return [(i.module_path, i.line, i.column + 1)
                for i in definitions if not i.in_builtin_module()]

    def _usages(self):
        """ Jedi "find usages" functionality

        :rtype: list of (str, int, int)
        """
        usages = self.script.usages()
        return [(i.module_path, i.line, i.column + 1)
                for i in usages if not i.in_builtin_module()]

    def _complete_call_assigments(self):
        """ Get function or class parameters and build Sublime Snippet string
        for completion

        :rtype: str
        """
        completions = []
        complete_all = self.auto_complete_function_params == 'all'

        try:
            call_definition = self.script.call_signatures()[0]
        except IndexError:
            call_definition = None

        parameters = get_function_parameters(call_definition, complete_all)

        for index, parameter in enumerate(parameters):
            name, value = parameter

            if value is None:
                completions.append('${%d:%s}' % (index + 1, name))
            elif complete_all:
                completions.append('%s=${%d:%s}' % (name, index + 1, value))

        return ", ".join(completions)
