# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
from logging import handlers
from optparse import OptionParser

import jedi
from jedi.api import NotFoundError


log = logging.getLogger('')
log.setLevel(logging.DEBUG)


def write(data):
    if not isinstance(data, str):
        data = json.dumps(data)
    sys.stdout.write(data)
    if not data.endswith('\n'):
        sys.stdout.write('\n')
    try:
        sys.stdout.flush()
    except IOError:
        sys.exit()

is_funcargs_complete_enabled = True
auto_complete_function_params = 'required'


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
    :rtype: list of (str, str)
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


def funcargs_from_script(script):
    """ Get completion in case we are in a function call

    :type script: jedi.api.Script
    :rtype: list of str
    """
    completions = []
    in_call = script.call_signatures()

    params = get_function_parameters(in_call)
    for code in params:
        if len(code) == 1:
            completions.append((code[0], '${1:%s}' % code[0]))
        else:
            completions.append((code[0] + '\t' + code[1],
                               '%s=${1:%s}' % (code[0], code[1])))
    return completions


def completions_from_script(script):
    """ regular completions

    :type script: jedi.api.Script
    :rtype: list of (str, str)
    """
    completions = script.completions()
    return [format_completion(complete) for complete in completions]


def goto_from_script(script):
    """ Jedi "go to Definitions" functionality

    :param script: jedi.api.Script
    :rtype: list of (str, in, int) or None
    """
    try:
        defns = script.goto_assignments()
    except NotFoundError:
        return
    else:
        return [(i.module_path, i.line, i.column)
                for i in defns if not i.in_builtin_module()]


def usages_from_script(script):
    """ Jedi "find usages" functionality

    :type script: jedi.api.Script
    :rtype: list of (str, in, int)
    """
    defns = script.usages()
    return [(i.module_path, i.line, i.column)
            for i in defns if not i.in_builtin_module()]


def funcrargs_from_script(script):
    """ Get function or class parameters and build Sublime Snippet string
    for completion

    :type script: jedi.api.Script
    :rtype: str
    """
    complete_all = auto_complete_function_params == 'all'
    parameters = get_function_parameters(script.call_signatures())

    completions = []
    for index, parameter in enumerate(parameters):
        try:
            name, value = parameter
        except IndexError:
            name = parameter[0]
            value = None

        if value is None:
            completions.append('${%d:%s}' % (index + 1, name))
        elif complete_all:
            completions.append('%s=${%d:%s}' % (name, index + 1, value))

    return ", ".join(completions)


def process_line(line):
    data = json.loads(line.strip())
    req_type = data.get('type', None)
    script = jedi.Script(data['source'], int(data['line']), int(data['offset']),
                         data['filename'] or '', 'utf-8')

    out_data = {'uuid': data['uuid'], 'type': data['type']}

    if req_type == 'autocomplete':
        out_data[req_type] = funcargs_from_script(script) or []
        out_data[req_type].extend(completions_from_script(script) or [])
    elif req_type == 'goto':
        out_data[req_type] = goto_from_script(script)
    elif req_type == 'usages':
        out_data[req_type] = usages_from_script(script)
    elif req_type == 'funcargs':
        out_data[req_type] = funcrargs_from_script(script)

    write(out_data)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-p", "--project", dest="project_name", default='',
                      help="project name to store jedi's cache")
    parser.add_option("-e", "--extra_folder", dest="extra_folders", default=[],
                      action="append", help="extra folders to add to sys.path")
    parser.add_option("-f", "--complete_function_params", dest="function_params",
                      default='all')

    options, args = parser.parse_args()

    is_funcargs_complete_enabled = bool(options.function_params)
    auto_complete_function_params = options.function_params

    if options.project_name:
        jedi.settings.cache_directory = os.path.join(
            jedi.settings.cache_directory,
            options.project_name,
        )
    if not os.path.exists(jedi.settings.cache_directory):
        os.makedirs(jedi.settings.cache_directory)
    hdlr = handlers.RotatingFileHandler(
        filename=os.path.join(jedi.settings.cache_directory, 'daemon.log'),
        maxBytes=10000000,
        backupCount=5,
        encoding='utf-8'
    )
    hdlr.setFormatter(logging.Formatter('%(asctime)s: %(levelname)-8s: %(message)s'))
    log.addHandler(hdlr)
    log.info(
        "started. cache directory - %s, extra folders - %s, complete_function_params - %s",
        jedi.settings.cache_directory,
        options.extra_folders,
        options.function_params,
    )

    for extra_folder in options.extra_folders:
        if extra_folder not in sys.path:
            sys.path.insert(0, extra_folder)

    for line in iter(sys.stdin.readline, ''):
        if line:
            try:
                process_line(line)
            except Exception:
                log.exception('failed to process line')
