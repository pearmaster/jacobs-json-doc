import unittest

from loader import PrepopulatedLoader
from resolver import PassThroughResolver
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
def:
    foo: "this is a foo string"
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
        ppl = PrepopulatedLoader()
        ppl.prepopulate(None, SIMPLE_YAML)
        doc = Document(uri=None, resolver=None, loader=ppl)
        
        self.assertEqual(doc['jacob'].line, 2)
        self.assertEqual(doc['jacob']['brunson'].line, 3)
        self.assertEqual(doc['jacob']['brunson'][0].line, 3)

    def test_local_ref_use_reference_objects(self):
        ppl = PrepopulatedLoader()
        ppl.prepopulate("yaml_with_ref", YAML_WITH_REF)
        doc = Document(uri="yaml_with_ref", resolver=None, loader=ppl, ref_resolution=RefResolutionMode.USE_REFERENCES_OBJECTS)
        self.assertIsInstance(doc['jacob']['local'], DocReference)
        node = doc['jacob']['local'].resolve()
        self.assertIsInstance(node, DocValue)
        self.assertEqual(node.value, "this is the value of the var")

    def test_local_ref_resolve_references(self):
        ppl = PrepopulatedLoader()
        ppl.prepopulate("local", YAML_WITH_REF)
        ppl.prepopulate("remote", SIMPLE_YAML)
        doc = Document(uri="local", resolver=PassThroughResolver(), loader=ppl, ref_resolution=RefResolutionMode.RESOLVE_REFERENCES)
        self.assertIsInstance(doc['jacob']['local'], DocValue)
        self.assertEqual(doc['jacob']['local'].value, "this is the value of the var")

    def test_remote_ref_use_reference_objects(self):
        ppl = PrepopulatedLoader()
        ppl.prepopulate("local", YAML_WITH_REF)
        ppl.prepopulate("remote", SIMPLE_YAML)
        doc = Document(uri="local", resolver=PassThroughResolver(), loader=ppl, ref_resolution=RefResolutionMode.USE_REFERENCES_OBJECTS)
        self.assertIsInstance(doc['jacob']['remote'], DocReference)
        node = doc['jacob']['remote'].resolve()
        self.assertIsInstance(node, DocValue)
        self.assertEqual(node.value, "this is a foo string")

    def test_remote_ref_resolve_references(self):
        ppl = PrepopulatedLoader()
        ppl.prepopulate("local", YAML_WITH_REF)
        ppl.prepopulate("remote", SIMPLE_YAML)
        doc = Document(uri="local", resolver=PassThroughResolver(), loader=ppl, ref_resolution=RefResolutionMode.RESOLVE_REFERENCES)
        self.assertIsInstance(doc['jacob']['remote'], DocValue)
        self.assertEqual(doc['jacob']['remote'].value, "this is a foo string")

if __name__ == '__main__':
    unittest.main()