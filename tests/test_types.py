import unittest

import jacobsjsondoc

JSON_WITH_A_TAB = """
{
    "things": [
        { "foo": "bar" },
		{ "hello": "world - this line has a tab character instead of spaces" },
        null
    ]
}
"""

class TestParsedTypes(unittest.TestCase):

    def setUp(self):
        self.doc = jacobsjsondoc.parse(JSON_WITH_A_TAB)

    def test_parse_json_with_tab(self):
        self.assertIsInstance(self.doc, dict)
        self.assertIsInstance(self.doc["things"], list)
        self.assertIsInstance(self.doc["things"][0], dict)
        self.assertIsNone(self.doc["things"][2])
