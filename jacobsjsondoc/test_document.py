import unittest

from loader import PrepopulatedLoader
from document import Document, RefResolutionMode, DocReference, DocValue

SIMPLE_YAML = """
jacob:
    brunson:
        - 1
        - 2
        - true
        - isa:
            nice guy
    food:
        true
"""

YAML_WITH_REF = """
jacob:
    var: "this is the value of the var"
    local:
        $ref: "#/jacob/var"
    remote:
        $ref: "remote#/def/foo"
"""



class TestDocument(unittest.TestCase):

    def test_lines(self):
        ppl = PrepopulatedLoader(SIMPLE_YAML)
        doc = Document(uri=None, resolver=None, loader=ppl)
        
        self.assertEqual(doc['jacob'].line, 2)
        self.assertEqual(doc['jacob']['brunson'].line, 3)
        self.assertEqual(doc['jacob']['brunson'][0].line, 3)

    def test_local_ref(self):
        ppl = PrepopulatedLoader(YAML_WITH_REF)
        doc = Document(uri=None, resolver=None, loader=ppl, ref_resolution=RefResolutionMode.USE_REFERENCES_OBJECTS)
        self.assertTrue(isinstance(doc['jacob']['local'], DocReference))
        node = doc['jacob']['local'].resolve()
        self.assertTrue(isinstance(node, DocValue))
        self.assertEqual(node.value, "this is the value of the var")

if __name__ == '__main__':
    unittest.main()