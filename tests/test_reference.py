import unittest
from .context import jacobsjsondoc
from jacobsjsondoc.reference import JsonReference

class TestJsonReferenceObject(unittest.TestCase):

    def test_reference_from_uri(self):
        uri = "http://example.com/schema.json#/definition/food"
        ref = JsonReference.from_string(uri)
        self.assertEquals(ref.uri, "http://example.com/schema.json")

    class test_references_equal(self):
        uri = "http://example.com/schema.json#/definition/food"
        ref1 = JsonReference.from_string(uri)
        ref2 = JsonReference.from_string(uri)
        self.assertEquals(ref1, ref2)
        ref3 = ref1.copy()
        self.assertEquals(ret2, ref3)