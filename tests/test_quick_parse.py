import unittest

import jacobsjsondoc
from jacobsjsondoc.document import DocObject

SUPER_SIMPLE_JSON = """
{
    "Hello": "Grand World"
}
"""

class TestQuickParse(unittest.TestCase):

    def test_quick_parse_json(self):
        doc = jacobsjsondoc.parse(SUPER_SIMPLE_JSON)
        self.assertIsInstance(doc, DocObject)