import unittest

from jacobsjsondoc.document import (
    DocObject,
    DocReference,
    UnableToLoadDocument,
    create_document,
)
from jacobsjsondoc.fetcher import PrepopulatedFetcher
from jacobsjsondoc.options import (
    ASYNCAPI_2,
    DRAFT_2020_12,
    OPENAPI_3_0,
    JsonSchemaParseOptions,
    RefResolutionMode,
)


class TestIdInEnumIsIgnored(unittest.TestCase):
    """A $id/$ref that happens to appear inside "enum"/"const" is arbitrary instance data, not a
    live schema keyword. This is the bug class the dialect/context system replaces the old
    parent-walking heuristics for.
    """

    def setUp(self):
        data = """
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "trap": {
                    "enum": [
                        {"$id": "https://localhost:1234/trap.json", "type": "null"},
                        {"$ref": "#/definitions/real"}
                    ]
                },
                "real": {
                    "$id": "https://localhost:1234/real.json",
                    "type": "string"
                }
            },
            "anyOf": [
                {"$ref": "https://localhost:1234/real.json"},
                {"$ref": "https://localhost:1234/trap.json"}
            ]
        }
        """
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("1", data)
        options = JsonSchemaParseOptions(dialect="draft-07")
        options.ref_resolution_mode = RefResolutionMode.USE_REFERENCES_OBJECTS
        self.doc = create_document(uri="1", fetcher=ppl, options=options)

    def test_real_id_resolves(self):
        resolved = self.doc["anyOf"][0].resolve()
        self.assertEqual(resolved["type"], "string")

    def test_id_in_enum_never_registered_as_a_resource(self):
        with self.assertRaises(UnableToLoadDocument):
            self.doc["anyOf"][1].resolve()

    def test_id_in_enum_is_still_plain_data(self):
        trap_entry = self.doc["definitions"]["trap"]["enum"][0]
        self.assertIsInstance(trap_entry, DocObject)
        self.assertEqual(trap_entry["$id"], "https://localhost:1234/trap.json")

    def test_ref_in_enum_is_still_plain_data(self):
        trap_entry = self.doc["definitions"]["trap"]["enum"][1]
        self.assertIsInstance(trap_entry, DocObject)
        self.assertNotIsInstance(trap_entry, DocReference)
        self.assertEqual(trap_entry["$ref"], "#/definitions/real")


class TestAnchorResolution(unittest.TestCase):
    def setUp(self):
        data = """
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://example.com/anchor-root.json",
            "$defs": {
                "foo": {
                    "$anchor": "fooAnchor",
                    "type": "string"
                }
            },
            "properties": {
                "bar": {"$ref": "#fooAnchor"}
            }
        }
        """
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("1", data)
        options = JsonSchemaParseOptions()
        options.ref_resolution_mode = RefResolutionMode.USE_REFERENCES_OBJECTS
        self.doc = create_document(uri="1", fetcher=ppl, options=options)

    def test_anchor_resolves_to_defs_foo(self):
        resolved = self.doc["properties"]["bar"].resolve()
        self.assertEqual(resolved["type"], "string")
        self.assertIs(resolved, self.doc["$defs"]["foo"])


class TestDynamicRefOuterWins(unittest.TestCase):
    """The classic "extensible base schema" idiom: an outer $dynamicAnchor should win over an
    inner one with the same name when reached via $dynamicRef, even though the $dynamicRef site
    is lexically inside the inner resource.
    """

    def setUp(self):
        data = """
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://example.com/root.json",
            "$dynamicAnchor": "node",
            "title": "outer-node",
            "$defs": {
                "inner": {
                    "$id": "https://example.com/inner.json",
                    "$dynamicAnchor": "node",
                    "title": "inner-node",
                    "type": "object",
                    "properties": {
                        "self": {"$dynamicRef": "#node"}
                    }
                }
            }
        }
        """
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("1", data)
        options = JsonSchemaParseOptions(dialect="2020-12")
        options.ref_resolution_mode = RefResolutionMode.USE_REFERENCES_OBJECTS
        self.doc = create_document(uri="1", fetcher=ppl, options=options)

    def test_outer_dynamic_anchor_wins(self):
        dynamic_ref = self.doc["$defs"]["inner"]["properties"]["self"]["$dynamicRef"]
        resolved = dynamic_ref.resolve()
        self.assertEqual(resolved["title"], "outer-node")


class TestRecursiveRefOuterWins(unittest.TestCase):
    """2019-09's $recursiveRef/$recursiveAnchor: the boolean-flagged idiom that $dynamicRef later
    replaced, sharing the same resource-chain machinery.
    """

    def setUp(self):
        data = """
        {
            "$schema": "https://json-schema.org/draft/2019-09/schema",
            "$id": "https://example.com/root.json",
            "$recursiveAnchor": true,
            "title": "outer",
            "$defs": {
                "inner": {
                    "$id": "https://example.com/inner.json",
                    "$recursiveAnchor": true,
                    "title": "inner",
                    "properties": {
                        "self": {"$recursiveRef": "#"}
                    }
                }
            }
        }
        """
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("1", data)
        options = JsonSchemaParseOptions(dialect="2019-09")
        options.ref_resolution_mode = RefResolutionMode.USE_REFERENCES_OBJECTS
        self.doc = create_document(uri="1", fetcher=ppl, options=options)

    def test_outer_recursive_anchor_wins(self):
        recursive_ref = self.doc["$defs"]["inner"]["properties"]["self"][
            "$recursiveRef"
        ]
        resolved = recursive_ref.resolve()
        self.assertEqual(resolved["title"], "outer")


class TestOpenApi30SchemaEmbedding(unittest.TestCase):
    def setUp(self):
        data = """
        {
            "openapi": "3.0.3",
            "info": {"title": "x", "version": "1.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "Pet": {
                        "type": "object",
                        "properties": {
                            "owner": {"$ref": "#/components/schemas/Owner"}
                        }
                    },
                    "Owner": {"type": "string"}
                }
            }
        }
        """
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("1", data)
        options = JsonSchemaParseOptions()  # auto-detect via "openapi" field
        options.ref_resolution_mode = RefResolutionMode.USE_REFERENCES_OBJECTS
        self.doc = create_document(uri="1", fetcher=ppl, options=options)

    def test_ref_inside_schemas_resolves(self):
        owner_ref = self.doc["components"]["schemas"]["Pet"]["properties"]["owner"]
        self.assertIsInstance(owner_ref, DocReference)
        resolved = owner_ref.resolve()
        self.assertEqual(resolved["type"], "string")

    def test_envelope_is_not_a_schema(self):
        # "info" is plain OpenAPI envelope data, not JSON Schema -- nothing special should be
        # inferred from it (e.g. it has no $id/$ref semantics).
        self.assertEqual(self.doc["info"]["title"], "x")


class TestSwagger2SchemaEmbedding(unittest.TestCase):
    def setUp(self):
        data = """
        {
            "swagger": "2.0",
            "info": {"title": "x", "version": "1.0"},
            "paths": {},
            "definitions": {
                "Pet": {
                    "type": "object",
                    "properties": {
                        "owner": {"$ref": "#/definitions/Owner"}
                    }
                },
                "Owner": {"type": "string"}
            }
        }
        """
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("1", data)
        options = JsonSchemaParseOptions()  # auto-detect via "swagger" field
        options.ref_resolution_mode = RefResolutionMode.USE_REFERENCES_OBJECTS
        self.doc = create_document(uri="1", fetcher=ppl, options=options)

    def test_ref_inside_definitions_resolves(self):
        owner_ref = self.doc["definitions"]["Pet"]["properties"]["owner"]
        self.assertIsInstance(owner_ref, DocReference)
        resolved = owner_ref.resolve()
        self.assertEqual(resolved["type"], "string")


class TestAsyncApi2PayloadEmbedding(unittest.TestCase):
    def setUp(self):
        data = """
        {
            "asyncapi": "2.6.0",
            "info": {"title": "x", "version": "1.0"},
            "channels": {
                "foo": {
                    "publish": {
                        "message": {
                            "payload": {
                                "type": "object",
                                "properties": {
                                    "bar": {"$ref": "#/components/schemas/Bar"}
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "Bar": {"type": "string"}
                }
            }
        }
        """
        ppl = PrepopulatedFetcher()
        ppl.prepopulate("1", data)
        options = JsonSchemaParseOptions()  # auto-detect via "asyncapi" field
        options.ref_resolution_mode = RefResolutionMode.USE_REFERENCES_OBJECTS
        self.doc = create_document(uri="1", fetcher=ppl, options=options)

    def test_ref_inside_payload_resolves(self):
        payload = self.doc["channels"]["foo"]["publish"]["message"]["payload"]
        bar_ref = payload["properties"]["bar"]
        self.assertIsInstance(bar_ref, DocReference)
        resolved = bar_ref.resolve()
        self.assertEqual(resolved["type"], "string")


class TestDialectSelection(unittest.TestCase):
    def test_explicit_dialect_by_name(self):
        options = JsonSchemaParseOptions(dialect="openapi-3.0")
        self.assertIs(options.resolve_dialect({"foo": "bar"}), OPENAPI_3_0)

    def test_explicit_dialect_wins_over_detection(self):
        options = JsonSchemaParseOptions(dialect="openapi-3.0")
        # Even though this structure looks like AsyncAPI, the explicit dialect wins.
        self.assertIs(options.resolve_dialect({"asyncapi": "2.6.0"}), OPENAPI_3_0)

    def test_unknown_dialect_name_raises(self):
        with self.assertRaises(ValueError):
            JsonSchemaParseOptions(dialect="not-a-real-dialect")

    def test_auto_detect_asyncapi(self):
        options = JsonSchemaParseOptions()
        self.assertIs(options.resolve_dialect({"asyncapi": "2.6.0"}), ASYNCAPI_2)

    def test_default_dialect_when_nothing_recognized(self):
        options = JsonSchemaParseOptions()
        self.assertIs(options.resolve_dialect({"type": "object"}), DRAFT_2020_12)


if __name__ == "__main__":
    unittest.main()
