import unittest
from .context import jacobsjsondoc
from jacobsjsondoc.reference import JsonReference, ReferenceDictionary
from jacobsjsondoc.document import create_document, RefResolutionMode
from jacobsjsondoc.loader import PrepopulatedLoader
from jacobsjsondoc.resolver import PassThroughResolver
import json

SAMPLE_DOCUMENT = {
    "$id": "http://example.com/schema.json",
    "type": "object",
    "properties": {
        "foo": {
            "$ref": "#fooprop",
        },
        "bar": {
            "$id": "#barprop",
            "type": "integer",
        }
    },
    "objects": {
        "fooProperty": {
            "$id": "#fooprop",
            "type": "string",
        }
    }
}

class TestJsonReferenceObject(unittest.TestCase):

    def test_reference_from_uri(self):
        uri = "http://example.com/schema.json#/definition/food"
        ref = JsonReference.from_string(uri)
        self.assertEquals(ref.uri, "http://example.com/schema.json")

    def test_references_equal(self):
        uri = "http://example.com/schema.json#/definition/food"
        ref1 = JsonReference.from_string(uri)
        ref2 = JsonReference.from_string(uri)
        self.assertEquals(ref1, ref2)
        ref3 = ref1.copy()
        self.assertEquals(ref2, ref3)

    def test_reference_buildup(self):
        base_uri = "http://example.com/myschema.json"
        ref = JsonReference.from_string(base_uri)
        change_path_id = "/other/schema.json"
        ref.change_to(JsonReference.from_string(change_path_id))
        self.assertEquals(ref.uri, "http://example.com/other/schema.json")
        add_fragment_id = "#func"
        ref.change_to(JsonReference.from_string(add_fragment_id))
        ref_repr = repr(ref)
        self.assertEquals(ref_repr, "http://example.com/other/schema.json#func")
        ref2 = JsonReference.from_string(ref_repr)
        self.assertEquals(ref, ref2)

class TestReferenceDictionary(unittest.TestCase):

    def setUp(self):
        self.data1 = {
            "A": {
                "B": 1,
                "C": [2,3,4,5]
            },
            "D": False
        }

    def test_reference_lookup(self):
        source_uri = "example"
        rd = ReferenceDictionary()
        rd.put(source_uri, self.data1)
        ref = JsonReference.from_string(source_uri)
        node_out = rd[ref]
        self.assertEqual(self.data1, node_out)
        ref.change_to(JsonReference.from_string("#A/B"))
        rd[ref] = self.data1['A']['B']
        fragment_uri = "example#A/B"
        self.assertEqual(rd.get(fragment_uri), 1)


class TestIdTagging(unittest.TestCase):

    def setUp(self):
        self.data = SAMPLE_DOCUMENT
        ppl = PrepopulatedLoader()
        ppl.prepopulate(self.data["$id"], json.dumps(self.data))
        self.doc = create_document(uri=self.data["$id"], resolver=PassThroughResolver(), loader=ppl, ref_resolution=RefResolutionMode.USE_REFERENCES_OBJECTS)
    
    def test_root_has_correct_id(self):
        self.assertEquals(self.doc._dollar_id.uri, self.data["$id"])

    def test_bar_has_correct_id(self):
        self.assertEquals(self.doc['properties']['bar']._dollar_id, "http://example.com/schema.json#barprop")

    def test_fooproperty_has_correct_id(self):
        self.assertEquals(self.doc['objects']['fooProperty']._dollar_id, "http://example.com/schema.json#fooprop")

    def test_dictionary_contents(self):
        print(self.doc._ref_dictionary)
        self.assertEqual(len(self.doc._ref_dictionary), 3)

    def test_dictionary_has_barprop(self):
        barprop = self.doc._ref_dictionary.get("http://example.com/schema.json#barprop")
        self.assertEquals(barprop['$id'], "#barprop")
        self.assertEquals(barprop['type'], "integer")
    
