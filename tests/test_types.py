import unittest

import jacobsjsondoc

JSON_WITH_A_TAB = """
{
    "things": [
        { "foo": "bar" },
		{ "hello": "world - this line has a tab character instead of spaces" },
        null,
        True,
        False
    ]
}
"""

class TestParsedTypes(unittest.TestCase):

    def setUp(self):
        self.doc = jacobsjsondoc.parse(JSON_WITH_A_TAB)

    def test_parse_dict(self):
        self.assertIsInstance(self.doc, dict)
        self.assertIsInstance(self.doc["things"][0], dict)
        self.assertIsNone(self.doc["things"][2])

    def test_parse_list(self):
        self.assertIsInstance(self.doc["things"], list)

    def test_parse_booleans(self):
        self.assertTrue(self.doc["things"][3])
        self.assertFalse(self.doc["things"][4])
        self.assertTrue(self.doc["things"][3] is True)
        self.assertTrue(self.doc["things"][4] is False)
