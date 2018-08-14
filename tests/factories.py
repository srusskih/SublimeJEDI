import sys
from jedi.api import environment

facade = sys.modules["Jedi - Python autocompletion.sublime_jedi.facade"]


def build_facade(source, line, column):
    env = environment.get_default_environment()
    return facade.JediFacade(
        env,
        'complete',
        source,
        line,
        column,
        sys_path=env.get_sys_path)
