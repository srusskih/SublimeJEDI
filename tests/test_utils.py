import sys
import unittest

utils = sys.modules["Jedi - Python autocompletion.sublime_jedi.utils"]


class SplitPathTestCase(unittest.TestCase):

    def test_split_paths_into_details(self):
        variables = {
            '$project': '/usr/bin/env',
            '$file': '/usr/bin/env',
        }
        utils.split_path(variables, ['$project'])

        self.assertEqual(variables, {
            '$file': '/usr/bin/env',
            '$project': '/usr/bin/env',
            '$project_path': '/usr/bin',
            '$project_name': 'env',
            '$project_base_name': 'env',
            '$project_extension': '',
        })


class ExpandPathTestCase(unittest.TestCase):

    def _test_populate_path_with_env_variables(self):
        result = utils.expand_path(
            {
                '$project_path': '/usr/bin',
            },
            '$project_path/env',
        )
        self.assertEqual(result, '/usr/bin/env')

    def _test_left_path_unchanged_if_expnded_path_doesnot_exists(self):
        result = utils.expand_path(
            {
                '$project_path': '/usr/bin',
            },
            '$project_path/envXXX',
        )
        self.assertEqual(result, '$project_path/envXXX')


class UniqueIterator(unittest.TestCase):

    def test_should_return_only_unique(self):
        actual = utils.unique([1, 1, 3])

        self.assertEqual(list(actual), [1, 3])

    def test_should_return_only_unique_with_predicator(self):
        actual = utils.unique([('a1\tparam', 'a1'),
                               ('a2\tparam', 'a2'),
                               ('a1\tparam', '${1:a1}')],
                              lambda x: x[0])

        self.assertEqual(list(actual), [('a1\tparam', 'a1'),
                                        ('a2\tparam', 'a2')])
