import unittest
from collections import defaultdict

from factories import build_facade

COMPLETE_WITH_SIGNATURE = '''
def a(a1, a2):
    pass

def b(b1, b2):
    pass

a('''


class ParametersCompletionTestCase(unittest.TestCase):

    def test_no_dups_in_function_signature_completion(self):
        """When we do function call completion
        we expect receive parameters as templates and
        all available statements to use in."""
        completions = list(build_facade(COMPLETE_WITH_SIGNATURE, 8, 2).
                           get_autocomplete())
        assert completions

        completions_map = defaultdict(list)
        [completions_map[l].append(v) for l, v in completions]

        self.assertEqual(completions_map['a1\tparam'], ['${1:a1}'])
        self.assertEqual(completions_map['a2\tparam'], ['${2:a2}'])
