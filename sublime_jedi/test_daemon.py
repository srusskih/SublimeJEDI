import json
import unittest
from contextlib import contextmanager


@contextmanager
def mock_stderr():
        from cStringIO import StringIO
        import sys

        _stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            yield sys.stderr
        finally:
            sys.stderr = _stderr


class RegressionIssue109(unittest.TestCase):
    """
    logging prints text and traceback to stderr. Then, code in `utils.py` can
    not parse output from daemon.py and there are a lot of messages in ST
    console with `Non JSON data from daemon`

    SHould be tested:

    1. content in stderr should be JSON valid
    2. content should contains correct data
    """

    def test_json_formatter_works_on_jedi_expections(self):

        with mock_stderr() as stderr_mock:
            from daemon import JediFacade  # load class here to mock stderr

            JediFacade('print "hello"', 1, 1).get('some')
            stderr_content = json.loads(stderr_mock.getvalue())

        self.assertEqual(stderr_content['logging'], 'error')
        self.assertIn('Traceback (most recent call last):',
                      stderr_content['content'])
        self.assertIn('JediFacade instance has no attribute \'get_some\'',
                      stderr_content['content'])


if __name__ == '__main__':
    unittest.main()