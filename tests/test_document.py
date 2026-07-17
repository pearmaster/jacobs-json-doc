import unittest
from jacobsjsondoc.fetcher import PrepopulatedFetcher
from jacobsjsondoc.document import (
    create_document,
    DocReference,
    DocValue,
    DocObject,
    CircularDependencyError,
)
from jacobsjsondoc.options import ParseOptions, RefResolutionMode

# remote
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

SIMPLE_WITH_INTEGER = """
thevalue: 42
"""

# middle
YAML_WITH_REF = """
house:
    var: "this is the value of the var"
    local:
        $ref: "#/house/var"
    remote:
        $ref: "remote#/def/foo"
"""

# local
ANOTHER_YAML_WITH_REF = """
colorado:
    denver: 1
    springs: 
        $ref: "middle#/house"
"""

YAML_TYPES = """
myobject:
    myint: 10
    myfloat: 3.14159
    mystring: string
    mytrue: true
    myfalse: false
    mynull: null
"""

YAML_WITH_ARRAY_OF_REFERENCES = """
anInt: 1
aNum: 1.1
aStr: "hi"
myarray:
    - $ref: "#/anInt"
    - $ref: "#/aNum"
    - $ref: "#/aStr" 
"""


class TestDocument(unittest.TestCase):

    def test_lines(self):
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("Simple", SIMPLE_YAML)
        doc = create_document(uri="Simple", fetcher=ppl)

        self.assertEqual(doc["jacob"].line, 2)
        self.assertEqual(doc["jacob"]["brunson"].line, 3)
        self.assertEqual(doc["jacob"]["brunson"][0].value, 1)
        self.assertEqual(doc["jacob"]["brunson"][0].line, 3)

    def test_indexes(self):
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("Simple", SIMPLE_YAML)
        doc = create_document(uri="Simple", fetcher=ppl)

        self.assertEqual(doc["jacob"].elem_index, "jacob")
        self.assertEqual(doc["jacob"]["brunson"].elem_index, "brunson")
        self.assertEqual(doc["jacob"]["brunson"][0].elem_index, 0)

    def test_array_ref_resolution(self):
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("Simple", YAML_WITH_ARRAY_OF_REFERENCES)
        options = ParseOptions()
        options.ref_resolution_mode = RefResolutionMode.RESOLVE_REFERENCES
        doc = create_document(uri="Simple", fetcher=ppl, options=options)
        self.assertEqual(doc["myarray"][0], 1)
        self.assertEqual(doc["myarray"][1], 1.1)
        self.assertEqual(doc["myarray"][2], "hi")

    def test_local_ref_use_reference_objects(self):
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("yaml_with_ref", YAML_WITH_REF)
        options = ParseOptions()
        options.ref_resolution_mode = RefResolutionMode.USE_REFERENCES_OBJECTS
        doc = create_document(uri="yaml_with_ref", fetcher=ppl, options=options)
        self.assertIsInstance(doc["house"]["local"], DocReference)
        node = doc["house"]["local"].resolve()
        self.assertIsInstance(node, DocValue)
        self.assertEqual(node.value, "this is the value of the var")

    def test_local_ref_resolve_references(self):
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("local", YAML_WITH_REF)
        ppl.prepopulate("remote", SIMPLE_YAML)
        options = ParseOptions()
        options.ref_resolution_mode = RefResolutionMode.RESOLVE_REFERENCES
        doc = create_document(uri="local", fetcher=ppl, options=options)
        self.assertIsInstance(doc["house"]["local"], DocValue)
        self.assertEqual(doc["house"]["local"].value, "this is the value of the var")

    def test_remote_ref_use_reference_objects(self):
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("local", YAML_WITH_REF)
        ppl.prepopulate("remote", SIMPLE_YAML)
        options = ParseOptions()
        options.ref_resolution_mode = RefResolutionMode.USE_REFERENCES_OBJECTS
        doc = create_document(uri="local", fetcher=ppl, options=options)
        self.assertIsInstance(doc["house"]["remote"], DocReference)
        node = doc["house"]["remote"].resolve()
        self.assertIsInstance(node, DocValue)
        self.assertEqual(node.value, "this is a foo string")
        self.assertEqual(node.line, 11)

    def test_remote_ref_resolve_references(self):
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("local", YAML_WITH_REF)
        ppl.prepopulate("remote", SIMPLE_YAML)
        options = ParseOptions()
        options.ref_resolution_mode = RefResolutionMode.RESOLVE_REFERENCES
        doc = create_document(uri="local", fetcher=ppl, options=options)
        self.assertIsInstance(doc["house"]["remote"], DocValue)
        self.assertEqual(doc["house"]["remote"].value, "this is a foo string")

    def test_3_layer_resolve_references(self):
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("middle", YAML_WITH_REF)
        ppl.prepopulate("remote", SIMPLE_YAML)
        ppl.prepopulate("local", ANOTHER_YAML_WITH_REF)
        options = ParseOptions()
        options.ref_resolution_mode = RefResolutionMode.RESOLVE_REFERENCES
        doc = create_document(uri="local", fetcher=ppl, options=options)
        self.assertIsInstance(doc["colorado"]["springs"], DocObject)
        self.assertIsInstance(doc["colorado"]["springs"]["var"], DocValue)
        self.assertEqual(
            doc["colorado"]["springs"]["var"].value, "this is the value of the var"
        )
        self.assertEqual(doc["colorado"]["springs"]["var"].uri_line, "middle:2")
        self.assertIsInstance(doc["colorado"]["springs"]["remote"], DocValue)
        self.assertEqual(
            doc["colorado"]["springs"]["remote"].value, "this is a foo string"
        )
        self.assertEqual(doc["colorado"]["springs"]["remote"].uri_line, "remote:11")

    def test_circular_dependency(self):
        yaml1 = """
        outer:
            inner:
                $ref: "two#/foo"
        """
        yaml2 = """
        foo:
            bar:
                $ref: "one#/outer"
        """
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("one", yaml1)
        ppl.prepopulate("two", yaml2)
        options = ParseOptions()
        options.ref_resolution_mode = RefResolutionMode.RESOLVE_REFERENCES
        with self.assertRaises(CircularDependencyError):
            create_document(uri="one", fetcher=ppl, options=options)

    def test_get_node_with_empty_string_key_segments(self):
        # A leading "/" produces a spurious empty leading token that should be
        # dropped, but an empty-string object key (an internal/trailing empty
        # segment) is a legitimate JSON Pointer segment and must be preserved.
        yaml_with_empty_key = """
        root:
            a:
                "":
                    value: 1
            "":
                value: 2
        """
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("Simple", yaml_with_empty_key)
        doc = create_document(uri="Simple", fetcher=ppl)

        root = doc["root"]
        self.assertIsInstance(root, DocObject)

        # "/" -> only the leading empty token is dropped, leaving a single ""
        # segment that resolves to the top-level empty-string key.
        node = root.get_node("/")
        self.assertIsInstance(node, DocObject)
        self.assertEqual(node["value"].value, 2)

        # "/a/" -> leading token dropped, but the trailing "" segment after
        # "a" is kept, resolving to root["a"][""].
        node = root.get_node("/a/")
        self.assertIsInstance(node, DocObject)
        self.assertEqual(node["value"].value, 1)

        self.assertTrue(root.has_node("/"))
        self.assertTrue(root.has_node("/a/"))
        self.assertFalse(root.has_node("/nonexistent"))


class TestDocumentTypes(unittest.TestCase):

    def setUp(self):
        ppl = PrepopulatedFetcher()
        ppl.prepopulate(None, YAML_TYPES)
        self.doc = create_document(uri=None, fetcher=ppl)

    def test_userdict(self):
        self.assertIsInstance(self.doc["myobject"], dict)

    def test_integer(self):
        self.assertEqual(self.doc["myobject"]["myint"], 10)
        self.assertIsInstance(self.doc["myobject"]["myint"], int)
        self.assertEqual(self.doc["myobject"]["myint"].line, 2)

    def test_float(self):
        self.assertEqual(self.doc["myobject"]["myfloat"], 3.14159)
        self.assertIsInstance(self.doc["myobject"]["myfloat"], float)
        self.assertEqual(self.doc["myobject"]["myfloat"].line, 3)

    def test_string(self):
        self.assertEqual(self.doc["myobject"]["mystring"], "string")
        self.assertIsInstance(self.doc["myobject"]["mystring"], str)
        self.assertEqual(self.doc["myobject"]["mystring"].line, 4)

    def test_boolean_true(self):
        self.assertEqual(self.doc["myobject"]["mytrue"], True)

    def test_boolean_false(self):
        self.assertEqual(self.doc["myobject"]["myfalse"], False)

    def test_null(self):
        self.assertEqual(self.doc["myobject"]["mynull"], None)
        self.assertIsInstance(self.doc["myobject"]["mynull"], type(None))


class TestDocumentSimpleTypes(unittest.TestCase):

    def test_integer(self):
        ppl = PrepopulatedFetcher()
        ppl.prepopulate(None, SIMPLE_WITH_INTEGER)
        self.doc = create_document(uri=None, fetcher=ppl)
        self.assertEqual(self.doc["thevalue"], 42)
        self.assertIsInstance(self.doc["thevalue"], int)
        self.assertEqual(self.doc["thevalue"].line, 1)


class TestDocumentReference(unittest.TestCase):

    def setUp(self):
        doc_text = """
        {
            "$ref": "http://example.org/schema"
        }
        """
        remote = """
        { "type": "integer" }
        """
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("local", doc_text)
        ppl.prepopulate("http://example.org/schema", remote)
        options = ParseOptions()
        options.ref_resolution_mode = RefResolutionMode.RESOLVE_REFERENCES
        self.doc = create_document(uri="local", fetcher=ppl, options=options)

    def test_loaded_reference(self):
        self.assertIsInstance(self.doc, dict)

    def test_correct_remote(self):
        print(self.doc)
        self.assertTrue("type" in self.doc)
        self.assertEqual(self.doc["type"], "integer")


class TestDocumentBooleanRoot(unittest.TestCase):

    def setUp(self):
        doc_text = "true"
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("true", doc_text)
        self.doc = create_document(uri="true", fetcher=ppl)

    def test_loads_boolean_root(self):
        self.assertTrue(self.doc)


if __name__ == "__main__":
    unittest.main()
