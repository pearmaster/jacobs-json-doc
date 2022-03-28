import unittest
from .context import jacobsjsondoc
from jacobsjsondoc.reference import JsonPointer
from jacobsjsondoc.document import create_document, DocReference, DocObject, Document, UnableToLoadDocument, PathReferenceResolutionError, DocString
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
        ref = JsonPointer.from_uri_string(uri)
        self.assertEqual(ref.uri, "http://example.com/schema.json")

    def test_references_equal(self):
        uri = "http://example.com/schema.json#/definition/food"
        ref1 = JsonPointer.from_uri_string(uri)
        ref2 = JsonPointer.from_uri_string(uri)
        self.assertEqual(ref1, ref2)
        ref3 = ref1.copy()
        self.assertEqual(ref2, ref3)

    def test_reference_buildup(self):
        base_uri = "http://example.com/myschema.json"
        ref = JsonPointer.from_uri_string(base_uri)
        change_path_id = "/other/schema.json"
        ref.to(JsonPointer.from_uri_string(change_path_id))
        self.assertEqual(ref.uri, "http://example.com/other/schema.json")
        add_fragment_id = "#func"
        ref.to(JsonPointer.from_uri_string(add_fragment_id))
        ref_repr = repr(ref)
        self.assertEqual(ref_repr, "http://example.com/other/schema.json#func")
        ref2 = JsonPointer.from_uri_string(ref_repr)
        self.assertEqual(ref, ref2)

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
            },
            "F": [
                "G",
                "H"
            ],
            "J" : { "$ref": "#/F/1" }
        }"""
        ppl = PrepopulatedLoader()
        ppl.prepopulate("data", data)
        options = ParseOptions()
        options.should_stop_dollar_id_parse = lambda: True
        self.doc = create_document(uri="data", loader=ppl)

    def test_dollar_ref_is_a_reference(self):
        self.assertIsInstance(self.doc["E"], DocReference)

    def test_object_with_property_that_isnt_a_reference(self):
        self.assertNotIsInstance(self.doc["A"], DocReference)
        self.assertIsInstance(self.doc["A"], DocObject)

    def test_not_a_reference(self):
        self.assertNotIsInstance(self.doc["A"]["$ref"], DocReference)
        self.assertIsInstance(self.doc["A"]["$ref"], DocObject)

    def test_array_index_reference(self):
        self.assertIsInstance(self.doc["J"], DocReference)
        self.assertEqual(self.doc["J"].resolve(), "H")

class TestIdTagging(unittest.TestCase):

    def setUp(self):
        self.data = SAMPLE_DOCUMENT
        ppl = PrepopulatedLoader()
        ppl.prepopulate(self.data["$id"], json.dumps(self.data))
        self.doc = create_document(uri=self.data["$id"], loader=ppl)
    
    def test_root_has_correct_id(self):
        self.assertEqual(self.doc.base_uri.uri, self.data["$id"])

    def test_bar_has_correct_id(self):
        self.assertEqual(self.doc['properties']['bar'].base_uri, "http://example.com/schema.json#barprop")

    def test_fooproperty_has_correct_id(self):
        self.assertEqual(self.doc['objects']['fooProperty'].base_uri, "http://example.com/schema.json#fooprop")

    def test_dictionary_has_barprop(self):
        barprop = self.doc._pointers.controller._document_cache["http://example.com/schema.json#barprop"]
        self.assertEqual(barprop['$id'], "#barprop")
        self.assertEqual(barprop['type'], "integer")
    
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
        ppl.prepopulate("1", self.data)
        self.doc = create_document(uri="1", loader=ppl)

    def test_is_a_reference(self):
        self.assertIsInstance(self.doc['items'][0], DocReference)
        resolved = self.doc['items'][0].resolve()
        self.assertEqual(resolved['type'], "array")
        self.assertIsInstance(resolved['items'], list)


ROOT_POINTER_REF = """
{
    "schema": {
        "properties": {
            "foo": {"$ref": "#"}
        },
        "additionalProperties": false
    }
}
"""

class TestRootPointerRef(unittest.TestCase):

    def setUp(self):
        self.data = ROOT_POINTER_REF
        ppl = PrepopulatedLoader()
        ppl.prepopulate("1", self.data)
        self.doc = create_document(uri="1", loader=ppl)

    def test_parses_root_pointer_ref(self):
        self.assertIsInstance(self.doc, Document)
        self.assertIn("schema", self.doc)
        self.assertIsInstance(self.doc["schema"]["properties"]["foo"], DocReference)

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
        ppl.prepopulate("1", data_text)
        options = ParseOptions()
        options.ref_resolution_mode = RefResolutionMode.USE_REFERENCES_OBJECTS
        options.dollar_id_token = "id"
        self.doc = create_document(uri="1", loader=ppl, options=options)

    def test_ref_points_to_correct_id(self):
        first_anyof_ref = self.doc["schema"]["anyOf"][0]
        self.assertIsInstance(first_anyof_ref, DocReference)
        second_anyof_ref = self.doc["schema"]["anyOf"][1]
        self.assertIsInstance(second_anyof_ref, DocReference)

        first_resolved = first_anyof_ref.resolve()
        second_resolved = second_anyof_ref.resolve()


class TestBaseUriChange(unittest.TestCase):

    def setUp(self):
        data_text = """
        {
            "id": "http://localhost:1234/scope_change_defs2.json",
            "type" : "object",
            "properties": {
                "list": {"$ref": "#/definitions/baz/definitions/bar"}
            },
            "definitions": {
                "baz": {
                    "id": "baseUriChangeFolderInSubschema/",
                    "definitions": {
                        "bar": {
                            "type": "array",
                            "items": {"$ref": "folderInteger.json"}
                        }
                    }
                }
            }
        }
        """
        data_text_2 = """
        {
            "id": "http://localhost:1234/",
            "items": {
                "id": "baseUriChange/",
                "items": {"$ref": "folderInteger.json"}
            }
        }"""
        data_text_3 = """
        {
            "$id": "http://example.com/schema-relative-uri-defs1.json",
            "properties": {
                "foo": {
                    "$id": "schema-relative-uri-defs2.json",
                    "definitions": {
                        "inner": {
                            "properties": {
                                "bar": { "type": "string" }
                            }
                        }
                    },
                    "allOf": [ { "$ref": "#/definitions/inner" } ]
                }
            },
            "allOf": [ { "$ref": "schema-relative-uri-defs2.json" } ]
        }"""
        ppl = PrepopulatedLoader()
        ppl.prepopulate("1", data_text)
        ppl.prepopulate("2", data_text_2)
        ppl.prepopulate("3", data_text_3)
        options = ParseOptions()
        options.ref_resolution_mode = RefResolutionMode.USE_REFERENCES_OBJECTS
        options.dollar_id_token = "id"
        self.doc = create_document(uri="1", loader=ppl, options=options)
        self.doc2 = create_document(uri="2", loader=ppl, options=options)
        options.dollar_id_token = "$id"
        self.doc3 = create_document(uri="3", loader=ppl, options=options)

    def test_types(self):
        self.assertIsInstance(self.doc["type"], str)
        self.assertIsInstance(self.doc["properties"], DocObject)
        self.assertIsInstance(self.doc["properties"]["list"], DocReference)
        self.assertIsInstance(self.doc["definitions"]["baz"]["definitions"]["bar"]["items"], DocReference)

        self.assertIsInstance(self.doc2["items"]["items"], DocReference)

        self.assertIsInstance(self.doc3["properties"]["foo"]["allOf"][0], DocReference)
        self.assertIsInstance(self.doc3["allOf"][0], DocReference)

    def test_dollar_ids1(self):
        self.assertEqual(self.doc.base_uri, "http://localhost:1234/scope_change_defs2.json")
        self.assertEqual(self.doc["definitions"]["baz"]["definitions"].base_uri, "http://localhost:1234/baseUriChangeFolderInSubschema/")

    def test_dollar_ids2(self):
        self.assertEqual(self.doc2.base_uri, "http://localhost:1234/")
        self.assertEqual(self.doc2["items"]["items"].base_uri, "http://localhost:1234/baseUriChange/")

    def test_dollar_ids3(self):
        self.assertEqual(self.doc3["properties"]["foo"].base_uri, "http://example.com/schema-relative-uri-defs2.json")

    def test_list_reference_resolution(self):
        dereffed = self.doc["properties"]["list"].resolve()
        self.assertIsInstance(dereffed, DocObject)

    def test_items_reference_resolution(self):
        with self.assertRaises(UnableToLoadDocument) as context:
            # We don't really want to have to load the remote reference, so we'll just check that the
            # exception shows the correct URI to the remote.
            dereffed = self.doc["definitions"]["baz"]["definitions"]["bar"]["items"].resolve()
            self.assertIn("http://localhost:1234/baseUriChangeFolderInSubschema/folderInteger.json", str(context.exception))

    def test_doc2_items_resolution(self):
        with self.assertRaises(UnableToLoadDocument) as context:
            # We don't really want to have to load the remote reference, so we'll just check that the
            # exception shows the correct URI to the remote.
            dereffed = self.doc2["items"]["items"].resolve()
            self.assertIn("http://localhost:1234/baseUriChange/folderInteger.json", str(context.exception))

    def test_doc3_resolution(self):
        self.assertIsInstance(self.doc3["properties"]["foo"]["allOf"][0], DocReference)
        self.assertIsInstance(self.doc3["allOf"][0], DocReference)

class TestInvalid(unittest.TestCase):

    def setUp(self):
        self.data = """
        foo:
            $ref: "#/doesnt/exist"
        bar:
            value: 1
        """
        ppl = PrepopulatedLoader()
        ppl.prepopulate("1", self.data)
        self.doc = create_document(uri="1", loader=ppl)
    
    def test_local_ref_goes_nowhere(self):
        self.assertIsInstance(self.doc['foo'], DocReference)
        with self.assertRaises(PathReferenceResolutionError) as context:
            self.doc['foo'].resolve()

class TestNotCircularDependency(unittest.TestCase):

    def setUp(self):
        self.data = """
        {
            '$id': "http://example.com/a.json", 
            '$defs': {
                'x': {
                    '$id': "http://example.com/b/c.json", 
                    'not': {
                        '$defs': {
                            'y': {
                                '$id': "d.json", 
                                'type': "number"
                            }
                        }
                    }
                }
            },
            'allOf': [
                '$ref': "http://example.com/b/d.json"
            ]
        }
        """
        ppl = PrepopulatedLoader()
        ppl.prepopulate("1", self.data)
        self.doc = create_document(uri="1", loader=ppl)
    
    def test_has_reference(self):
        self.assertIsInstance(self.doc['allOf'][0], DocReference)

    def test_reference_isnt_circular_dependency(self):
        resolved_doc = self.doc['allOf'][0].resolve()
        self.assertIsInstance(resolved_doc, DocObject)
        self.assertIn('type', resolved_doc)
        self.assertEqual(resolved_doc['type'], "number")


class TestRefPropertyWithOthers(unittest.TestCase):

    def setUp(self):
        self.data = """
        $defs: 
            valueRange:
                minimum: 0
                maximum: 0
        type: integer
        $ref: "#/$defs/valueRange"
        """
        ppl = PrepopulatedLoader()
        ppl.prepopulate("1", self.data)
        opts = ParseOptions()
        opts.ref_resolution_mode = RefResolutionMode.RESOLVE_WHEN_REQUIRED
        self.doc = create_document(uri="1", loader=ppl, options=opts)
    
    def test_is_object(self):
        self.assertIsInstance(self.doc, DocObject)

    def test_is_for_integer(self):
        self.assertIsInstance(self.doc['type'], DocString)
        self.assertEqual(self.doc['type'], "integer")

    def test_ref_resolved(self):
        self.assertNotIn("$ref", self.doc)

    def test_has_minimum(self):
        self.assertIsInstance(self.doc['minimum'], int)
        self.assertEqual(self.doc['minimum'], 0)
    
    def test_has_maximum(self):
        self.assertIsInstance(self.doc['maximum'], int)
        self.assertEqual(self.doc['maximum'], 0)