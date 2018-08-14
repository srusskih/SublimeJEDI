import sys
import unittest
from jedi.api import environment


facade = sys.modules["Jedi - Python autocompletion.sublime_jedi.facade"]


COMPLETION_TEST = '''
def func(var1, var2):
    va'''


class ParametersCompletionTestCase(unittest.TestCase):

    def test_should_return_function_parameters_also(self):
        env = environment.get_default_environment()
        f = facade.JediFacade(
            env,
            'complete',
            COMPLETION_TEST,
            3, 6,
            sys_path=env.get_sys_path)

        completions = f.get_autocomplete()
        assert completions

        self.assertIn(('var1\tparam', 'var1'), completions)
        self.assertIn(('var2\tparam', 'var2'), completions)
