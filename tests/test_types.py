import unittest
import os.path

import jacobsjsondoc

JSON_WITH_A_TAB = """
{
    "things": [
        { "foo": "bar" },
		{ "hello": "world - this line has a tab character instead of spaces" },
        null,
        True,
        False
    ],
    "hi": "💩"
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

    def test_grapheme(self):
        self.assertIsInstance(self.doc["hi"], str)
        self.assertEqual(self.doc["hi"], "💩")

class TestMinLength(unittest.TestCase):

    def setUp(self):
        data_file = os.path.join(os.path.dirname(__file__), "minLength.json")
        with open(data_file, "r") as data:
            self.doc = jacobsjsondoc.parse(data.read())

    def test_grapheme(self):
        self.assertIsInstance("💩", str)
        self.assertEqual(len("💩"), 1)
        self.assertIsInstance(self.doc["data"], str)
        self.assertIsInstance(self.doc["data"], jacobsjsondoc.document.DocString)
        #self.assertEqual(self.doc[0]["tests"][4]["data"], "💩")
        self.assertEqual(len(self.doc["data"]), 1)
