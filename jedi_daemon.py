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


def format(complete):
    """ Returns a tuple of the string that would be visible in the completion
        dialogue, and the snippet to insert for the completion

        :param complete: `jedi.api.Complete` object
        :return: tuple(string, string)
    """
    display, insert = complete.word + '\t' + complete.type, complete.word
    if not is_funcargs_complete_enabled:
        if complete.type == 'function':
            # if its a function add parentheses
            return display, insert + "(${1})"
        return display, insert

    if hasattr(complete.definition, 'params'):
        params = []
        for index, param in enumerate(complete.definition.params):
            # Strip all whitespace to make it PEP8 compatible
            code = [s.strip() for s in param.get_code().strip().split('=')]
            if 'self' in code or code[0].startswith('*'):
                # drop self and *args, **kwargs from method calls
                continue
            if len(code) > 1 and auto_complete_function_params == 'all':
                # param with default value
                params.append("%s=${%d:%s}" % (code[0], index + 1, code[1]))
            elif len(code) == 1:
                # required param
                params.append("${%d:%s}" % (index + 1, code[0]))
        insert = "%(fname)s(%(params)s)" % {
            'fname': insert,
            'params': ', '.join(params)
        }
    return display, insert


def funcargs_from_script(script):
    """ get completion in case we are in a function call """
    completions = []
    in_call = script.get_in_function_call()
    if in_call is not None:
        for calldef in in_call.params:
            # Strip all whitespace to make it PEP8 compatible
            code = calldef.get_code().strip()
            if '*' in code or code == 'self':
                continue
            code = [s.strip() for s in code.split('=')]
            if len(code) == 1:
                completions.append((code[0], '%s=${1}' % code[0]))
            else:
                completions.append((code[0] + '\t' + code[1],
                                   '%s=${1:%s}' % (code[0], code[1])))
    return completions


def completions_from_script(script):
    """ regular completions """
    completions = script.complete()
    return [format(complete) for complete in completions]


def goto_from_script(script):
    for method in ['get_definition', 'goto']:
        try:
            defns = getattr(script, method)()
        except NotFoundError:
            pass
        else:
            return [(i.module_path, i.line, i.column)
                    for i in defns if not i.in_builtin_module()
                    ]


def usages_from_script(script):
    return [(i.module_path, i.line, i.column)
            for i in script.related_names() if not i.in_builtin_module()
            ]


def process_line(line):
    data = json.loads(line.strip())
    req_type = data.get('type', None)
    if req_type in ['autocomplete', 'goto', 'usages']:
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

        write(out_data)
    elif req_type == 'configure':
        reconfigure(data)

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
