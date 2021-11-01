import unittest

import jacobsjsondoc
from jacobsjsondoc.parser import Parser

JSON_WITH_A_TAB = """
{
    "things": [
        { "foo": "bar" },
		{ "hello": "world - this line has a tab character instead of spaces" }
    ]
}
"""

class TestParseJson(unittest.TestCase):

    def setUp(self):
        self.parser = Parser()

    def test_parse_json_with_tab(self):
        doc = self.parser.parse_json(JSON_WITH_A_TAB)
        self.assertIsInstance(doc, dict)
        self.assertIsInstance(doc["things"], list)
