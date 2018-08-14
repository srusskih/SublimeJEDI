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
