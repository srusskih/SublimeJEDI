# -*- coding: utf-8 -*-
import os
import sys
import json
import logging
from optparse import OptionParser

# add jedi too sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import jedi
from jedi.api import NotFoundError

# remove it. WHY?
sys.path.pop(0)

is_funcargs_complete_enabled = True
auto_complete_function_params = 'required'


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


def write(data):
    """  Write data to STDOUT """
    if not isinstance(data, str):
        data = json.dumps(data)

    sys.stdout.write(data)

    if not data.endswith('\n'):
        sys.stdout.write('\n')

    try:
        sys.stdout.flush()
    except IOError:
        sys.exit()


def format_completion(complete):
    """ Returns a tuple of the string that would be visible in
    the completion dialogue and the completion word

    :type complete: jedi.api_classes.Completion
    :rtype: (str, str)
    """
    display, insert = complete.name + '\t' + complete.type, complete.name
    return display, insert


def get_function_parameters(callDef):
    """  Return list function parameters, prepared for sublime completion.
    Tuple contains parameter name and default value

    Parameters list excludes: self, *args and **kwargs parameters

    :type callDef: jedi.api_classes.CallDef
    :rtype: list of (str, str or None)
    """
    if not callDef:
        return []

    params = []
    for param in callDef.params:
        cleaned_param = param.get_code().strip()
        if '*' in cleaned_param or cleaned_param == 'self':
            continue
        params.append([s.strip() for s in cleaned_param.split('=')])
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
    def __init__(self, source, line, offset, filename='', encoding='utf-8'):
        self.script = jedi.Script(
            source, int(line), int(offset), filename, encoding
        )

    def get(self, action):
        """ Action dispatcher """
        try:
            return getattr(self, 'get_' + action)()
        except:
            logger.exception('`JediFacade.get_{0}` failed'.format(action))

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
        data = self._parameters_for_completion() or []
        data.extend(self._completion() or [])
        return data

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
            try:
                name, value = parameter
            except ValueError:
                name = parameter[0]
                value = None

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
        try:
            definitions = self.script.goto_assignments()
            if all(d.type == 'import' for d in definitions):
                # check if it an import string and if it is get definition
                definitions = self.script.get_definition()
        except NotFoundError:
            return
        else:
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
        complete_all = auto_complete_function_params == 'all'

        try:
            call_definition = self.script.call_signatures()[0]
        except IndexError:
            call_definition = None

        parameters = get_function_parameters(call_definition)

        for index, parameter in enumerate(parameters):
            try:
                name, value = parameter
            except ValueError:
                name = parameter[0]
                value = None

            if value is None:
                completions.append('${%d:%s}' % (index + 1, name))
            elif complete_all:
                completions.append('%s=${%d:%s}' % (name, index + 1, value))

        return ", ".join(completions)


def process_line(line):
    data = json.loads(line.strip())
    action_type = data['type']

    script = JediFacade(
        source=data['source'],
        line=data['line'],
        offset=data['offset'],
        filename=data.get('filename', '')
    )

    out_data = {
        'uuid': data.get('uuid'),
        'type': action_type,
        action_type: script.get(action_type)
    }

    write(out_data)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option(
        "-p", "--project",
        dest="project_name",
        default='',
        help="project name to store jedi's cache"
    )
    parser.add_option(
        "-e", "--extra_folder",
        dest="extra_folders",
        default=[],
        action="append",
        help="extra folders to add to sys.path"
    )
    parser.add_option(
        "-f", "--complete_function_params",
        dest="function_params",
        default='all',
        help='function parameters completion type: "all", "required", or ""'
    )

    options, args = parser.parse_args()

    is_funcargs_complete_enabled = bool(options.function_params)
    auto_complete_function_params = options.function_params

    logger.info(
        'Daemon started. '
        'extra folders - %s, '
        'complete_function_params - %s',
        options.extra_folders,
        options.function_params,
    )

    # append extra paths to sys.path
    for extra_folder in options.extra_folders:
        if extra_folder not in sys.path:
            sys.path.insert(0, extra_folder)

    # call the Jedi
    for line in iter(sys.stdin.readline, ''):
        if line:
            try:
                process_line(line)
            except Exception:
                logger.exception('failed to process line')
