import unittest
from .context import jacobsjsondoc
from jacobsjsondoc.reference import JsonAnchor, ReferenceDictionary
from jacobsjsondoc.document import create_document, DocReference, DocObject
from jacobsjsondoc.loader import PrepopulatedLoader
from jacobsjsondoc.options import ParseOptions, RefResolutionMode
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
        ref = JsonAnchor.from_string(uri)
        self.assertEquals(ref.uri, "http://example.com/schema.json")

    def test_references_equal(self):
        uri = "http://example.com/schema.json#/definition/food"
        ref1 = JsonAnchor.from_string(uri)
        ref2 = JsonAnchor.from_string(uri)
        self.assertEquals(ref1, ref2)
        ref3 = ref1.copy()
        self.assertEquals(ref2, ref3)

    def test_reference_buildup(self):
        base_uri = "http://example.com/myschema.json"
        ref = JsonAnchor.from_string(base_uri)
        change_path_id = "/other/schema.json"
        ref.change_to(JsonAnchor.from_string(change_path_id))
        self.assertEquals(ref.uri, "http://example.com/other/schema.json")
        add_fragment_id = "#func"
        ref.change_to(JsonAnchor.from_string(add_fragment_id))
        ref_repr = repr(ref)
        self.assertEquals(ref_repr, "http://example.com/other/schema.json#func")
        ref2 = JsonAnchor.from_string(ref_repr)
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
        ref = JsonAnchor.from_string(source_uri)
        node_out = rd[ref]
        self.assertEqual(self.data1, node_out)
        ref.change_to(JsonAnchor.from_string("#A/B"))
        rd[ref] = self.data1['A']['B']
        fragment_uri = "example#A/B"
        self.assertEqual(rd.get(fragment_uri), 1)

class TestNotAReference(unittest.TestCase):

    def setUp(self):
        data = """{
            "A": {
                "B": 1,
                "$ref": {"C":true}
            },
            "D": false,
            "E": {
                "$ref": "#/A"
            }
        }"""
        ppl = PrepopulatedLoader()
        ppl.prepopulate("data", data)
        self.doc = create_document(uri="data", loader=ppl)

    def test_dollar_ref_is_a_reference(self):
        self.assertIsInstance(self.doc["E"], DocReference)

    def test_object_with_property_that_isnt_a_reference(self):
        self.assertNotIsInstance(self.doc["A"], DocReference)
        self.assertIsInstance(self.doc["A"], DocObject)

    def test_not_a_reference(self):
        self.assertNotIsInstance(self.doc["A"]["$ref"], DocReference)
        self.assertIsInstance(self.doc["A"]["$ref"], DocObject)

class TestIdTagging(unittest.TestCase):

    def setUp(self):
        self.data = SAMPLE_DOCUMENT
        ppl = PrepopulatedLoader()
        ppl.prepopulate(self.data["$id"], json.dumps(self.data))
        self.doc = create_document(uri=self.data["$id"], loader=ppl)
    
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
    
DOUBLE_REFERENCE_DOC = """
{
    "definitions": {
        "item": {
            "type": "array",
            "additionalItems": false,
            "items": [
                { "$ref": "#/definitions/sub-item" },
                { "$ref": "#/definitions/sub-item" }
            ]
        },
        "sub-item": {
            "type": "object",
            "required": ["foo"]
        }
    },
    "type": "array",
    "additionalItems": false,
    "items": [
        { "$ref": "#/definitions/item" },
        { "$ref": "#/definitions/item" },
        { "$ref": "#/definitions/item" }
    ]
}
"""

class TestDoubleRef(unittest.TestCase):

    def setUp(self):
        self.data = DOUBLE_REFERENCE_DOC
        ppl = PrepopulatedLoader()
        ppl.prepopulate(1, self.data)
        self.doc = create_document(uri=1, loader=ppl)

    def test_is_a_reference(self):
        self.assertIsInstance(self.doc['items'][0], DocReference)
        resolved = self.doc['items'][0].resolve()
        self.assertEqual(resolved['type'], "array")
        self.assertIsInstance(resolved['items'], list)

class TestIdTrouble(unittest.TestCase):

    def setUp(self):
        data_text = """
        "schema": {
            "definitions": {
                "id_in_enum": {
                    "enum": [
                        {
                          "id": "https://localhost:1234/my_identifier.json",
                          "type": "null"
                        }
                    ]
                },
                "real_id_in_schema": {
                    "id": "https://localhost:1234/my_identifier.json",
                    "type": "string"
                },
                "zzz_id_in_const": {
                    "const": {
                        "id": "https://localhost:1234/my_identifier.json",
                        "type": "null"
                    }
                }
            },
            "anyOf": [
                { "$ref": "#/schema/definitions/id_in_enum" },
                { "$ref": "https://localhost:1234/my_identifier.json" }
            ]
        }
        """
        ppl = PrepopulatedLoader()
        ppl.prepopulate(1, data_text)
        options = ParseOptions()
        options.ref_resolution_mode = RefResolutionMode.USE_REFERENCES_OBJECTS
        options.dollar_id_token = "id"
        self.doc = create_document(uri=1, loader=ppl, options=options)

    def test_ref_points_to_correct_id(self):
        first_anyof_ref = self.doc["schema"]["anyOf"][0]
        self.assertIsInstance(first_anyof_ref, DocReference)
        second_anyof_ref = self.doc["schema"]["anyOf"][1]
        self.assertIsInstance(second_anyof_ref, DocReference)

        first_resolved = first_anyof_ref.resolve()
        second_resolved = second_anyof_ref.resolve()
        