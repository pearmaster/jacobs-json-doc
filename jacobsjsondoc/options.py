from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Union

IndexKey = Union[str, int]


class RefResolutionMode(Enum):
    USE_REFERENCES_OBJECTS = 0
    RESOLVE_REFERENCES = 1
    RESOLVE_MERGE_PROPERTIES = 2


class NodeContext(Enum):
    """Where a node sits, structurally, with respect to the active dialect's vocabulary.

    SCHEMA                 -- this node *is* a schema. $id/$anchor/$ref/$dynamicRef etc. are live
                               here.
    SCHEMA_MAP_CONTAINER    -- this node's values are each a schema (e.g. "properties", "$defs").
    SCHEMA_ARRAY_CONTAINER  -- this node's items are each a schema (e.g. "allOf", "prefixItems").
    MIXED_MAP_CONTAINER     -- this node's values are a schema if a dict, otherwise plain data
                               (legacy "dependencies" keyword).
    STRUCTURAL              -- this node is part of a non-schema envelope (e.g. an OpenAPI/AsyncAPI
                               document body) that may still embed schemas at known locations.
    DATA                    -- this node is arbitrary instance data (e.g. inside "enum"/"const"/
                               "default"/"examples", or an unrecognized keyword). Nothing here is
                               ever interpreted as $id/$ref/$anchor/etc., and this is contagious to
                               every descendant.
    """

    SCHEMA = "schema"
    SCHEMA_MAP_CONTAINER = "schema_map_container"
    SCHEMA_ARRAY_CONTAINER = "schema_array_container"
    MIXED_MAP_CONTAINER = "mixed_map_container"
    STRUCTURAL = "structural"
    DATA = "data"


class ApplicatorKind(Enum):
    """Describes the shape of the value found at a schema-bearing keyword."""

    SINGLE_SCHEMA = "single_schema"
    SCHEMA_MAP = "schema_map"
    SCHEMA_ARRAY = "schema_array"
    SCHEMA_OR_SCHEMA_ARRAY = "schema_or_schema_array"
    MIXED_MAP = "mixed_map"


class ReferenceKind(Enum):
    PLAIN = "plain"
    DYNAMIC = "dynamic"
    RECURSIVE = "recursive"


@dataclass(frozen=True)
class ReferenceMatch:
    kind: ReferenceKind
    keyword: str
    value: str


@dataclass(frozen=True)
class AnchorMatch:
    plain_name: Optional[str] = None
    dynamic_name: Optional[str] = None

    @property
    def is_empty(self) -> bool:
        return self.plain_name is None and self.dynamic_name is None


@dataclass(frozen=True)
class Dialect:
    """A table-driven description of a JSON Schema / OpenAPI / AsyncAPI vocabulary.

    This is pure data. All behavior lives on `ParseOptions`/`JsonSchemaParseOptions`, which are the
    only things `document.py` talks to; `document.py` never inspects a `Dialect` directly.
    """

    name: str
    root_context: NodeContext = NodeContext.SCHEMA
    id_keyword: Optional[str] = "$id"
    ref_keyword: str = "$ref"
    anchor_keyword: Optional[str] = None
    dynamic_ref_keyword: Optional[str] = None
    dynamic_anchor_keyword: Optional[str] = None
    recursive_ref_keyword: Optional[str] = None
    recursive_anchor_keyword: Optional[str] = None
    applicators: Dict[str, ApplicatorKind] = field(default_factory=dict)
    structural_entry_keywords: Dict[str, ApplicatorKind] = field(default_factory=dict)


def _context_for_kind(kind: ApplicatorKind, value: Any) -> NodeContext:
    if kind == ApplicatorKind.SINGLE_SCHEMA:
        return NodeContext.SCHEMA
    if kind == ApplicatorKind.SCHEMA_MAP:
        return NodeContext.SCHEMA_MAP_CONTAINER
    if kind == ApplicatorKind.SCHEMA_ARRAY:
        return NodeContext.SCHEMA_ARRAY_CONTAINER
    if kind == ApplicatorKind.SCHEMA_OR_SCHEMA_ARRAY:
        return (
            NodeContext.SCHEMA_ARRAY_CONTAINER
            if isinstance(value, list)
            else NodeContext.SCHEMA
        )
    if kind == ApplicatorKind.MIXED_MAP:
        return NodeContext.MIXED_MAP_CONTAINER
    return NodeContext.DATA


def classify_child(
    dialect: Dialect, context: NodeContext, key: IndexKey, value: Any
) -> NodeContext:
    """Compute the `NodeContext` for a child found at `key` (with raw `value`) of a node
    currently in `context`. This is the single, table-driven replacement for the old
    parent-walking heuristics.
    """
    if context == NodeContext.DATA:
        return NodeContext.DATA
    if context == NodeContext.SCHEMA_MAP_CONTAINER:
        return NodeContext.SCHEMA
    if context == NodeContext.SCHEMA_ARRAY_CONTAINER:
        return NodeContext.SCHEMA
    if context == NodeContext.MIXED_MAP_CONTAINER:
        return NodeContext.SCHEMA if isinstance(value, dict) else NodeContext.DATA
    if context == NodeContext.STRUCTURAL:
        if isinstance(key, str) and key in dialect.structural_entry_keywords:
            return _context_for_kind(dialect.structural_entry_keywords[key], value)
        return NodeContext.STRUCTURAL
    # context == NodeContext.SCHEMA
    if isinstance(key, str) and key in dialect.applicators:
        return _context_for_kind(dialect.applicators[key], value)
    return NodeContext.DATA


class ParseOptions:
    """The naive/base strategy: no dialect awareness at all. Any `$ref`/`$id` (or whatever tokens
    are configured) is honored unconditionally, everywhere -- this is the historical behavior of
    this library, kept as-is for callers that don't need JSON Schema/OpenAPI/AsyncAPI smarts.
    """

    def __init__(self) -> None:
        self.ref_resolution_mode: RefResolutionMode = (
            RefResolutionMode.USE_REFERENCES_OBJECTS
        )
        self.dollar_id_token: str = "$id"
        self.dollar_ref_token: str = "$ref"

    def resolve_dialect(self, structure: Any) -> Optional[Dialect]:
        return None

    def initial_context(self, dialect: Optional[Dialect]) -> NodeContext:
        return NodeContext.SCHEMA

    def classify_child(
        self,
        dialect: Optional[Dialect],
        context: NodeContext,
        key: IndexKey,
        value: Any,
    ) -> NodeContext:
        return context

    def get_base_uri(
        self, dialect: Optional[Dialect], context: NodeContext, node: Any
    ) -> Optional[str]:
        value = node.get(self.dollar_id_token)
        if isinstance(value, str):
            return value
        return None

    def get_reference(
        self, dialect: Optional[Dialect], context: NodeContext, node: Any
    ) -> Optional[ReferenceMatch]:
        value = node.get(self.dollar_ref_token)
        if isinstance(value, str):
            return ReferenceMatch(ReferenceKind.PLAIN, self.dollar_ref_token, value)
        return None

    def get_dynamic_reference(
        self, dialect: Optional[Dialect], context: NodeContext, node: Any
    ) -> Optional[ReferenceMatch]:
        return None

    def get_anchors(
        self, dialect: Optional[Dialect], context: NodeContext, node: Any
    ) -> AnchorMatch:
        return AnchorMatch()

    def reference_keyword(self, dialect: Optional[Dialect]) -> str:
        return self.dollar_ref_token


class JsonSchemaParseOptions(ParseOptions):
    """The dialect-aware strategy used to parse JSON Schema (any draft), OpenAPI (any version), and
    AsyncAPI (any version) documents.

    A `JsonSchemaParseOptions` can be obtained three ways:
      1. Manually, by passing a custom `Dialect` -- for a bespoke/extended vocabulary.
      2. Explicitly, by name -- e.g. `JsonSchemaParseOptions(dialect="openapi-3.0")`.
      3. Automatically -- default construction inspects each document's `$schema`/`openapi`/
         `asyncapi`/`swagger` fields at parse time and selects a built-in dialect.

    `document.py` never looks at a `Dialect` (or a dialect name) directly -- it only calls methods
    on this object, passing along whatever (opaque, to it) dialect value `resolve_dialect()` handed
    back for the current document.
    """

    def __init__(
        self,
        dialect: Optional[Union[str, Dialect]] = None,
        default_dialect: Union[str, Dialect] = "2020-12",
        auto_detect: bool = True,
    ) -> None:
        super().__init__()
        self.explicit_dialect: Optional[Dialect] = _coerce_dialect(dialect)
        self.auto_detect: bool = auto_detect and self.explicit_dialect is None
        resolved_default = _coerce_dialect(default_dialect)
        assert resolved_default is not None
        self.default_dialect: Dialect = resolved_default

    def resolve_dialect(self, structure: Any) -> Dialect:
        if self.explicit_dialect is not None:
            return self.explicit_dialect
        if self.auto_detect:
            detected = detect_dialect(structure)
            if detected is not None:
                return detected
        return self.default_dialect

    def initial_context(self, dialect: Optional[Dialect]) -> NodeContext:
        assert dialect is not None
        return dialect.root_context

    def classify_child(
        self,
        dialect: Optional[Dialect],
        context: NodeContext,
        key: IndexKey,
        value: Any,
    ) -> NodeContext:
        assert dialect is not None
        return classify_child(dialect, context, key, value)

    def get_base_uri(
        self, dialect: Optional[Dialect], context: NodeContext, node: Any
    ) -> Optional[str]:
        assert dialect is not None
        if context != NodeContext.SCHEMA or dialect.id_keyword is None:
            return None
        value = node.get(dialect.id_keyword)
        if isinstance(value, str):
            return value
        return None

    def get_reference(
        self, dialect: Optional[Dialect], context: NodeContext, node: Any
    ) -> Optional[ReferenceMatch]:
        assert dialect is not None
        if context == NodeContext.DATA:
            return None
        value = node.get(dialect.ref_keyword)
        if isinstance(value, str):
            return ReferenceMatch(ReferenceKind.PLAIN, dialect.ref_keyword, value)
        return None

    def get_dynamic_reference(
        self, dialect: Optional[Dialect], context: NodeContext, node: Any
    ) -> Optional[ReferenceMatch]:
        assert dialect is not None
        if context != NodeContext.SCHEMA:
            return None
        if dialect.dynamic_ref_keyword is not None:
            value = node.get(dialect.dynamic_ref_keyword)
            if isinstance(value, str):
                return ReferenceMatch(
                    ReferenceKind.DYNAMIC, dialect.dynamic_ref_keyword, value
                )
        if dialect.recursive_ref_keyword is not None:
            value = node.get(dialect.recursive_ref_keyword)
            if isinstance(value, str):
                return ReferenceMatch(
                    ReferenceKind.RECURSIVE, dialect.recursive_ref_keyword, value
                )
        return None

    def get_anchors(
        self, dialect: Optional[Dialect], context: NodeContext, node: Any
    ) -> AnchorMatch:
        assert dialect is not None
        if context != NodeContext.SCHEMA:
            return AnchorMatch()
        plain_name: Optional[str] = None
        dynamic_name: Optional[str] = None
        if dialect.anchor_keyword is not None:
            value = node.get(dialect.anchor_keyword)
            if isinstance(value, str):
                plain_name = value
        if dialect.dynamic_anchor_keyword is not None:
            value = node.get(dialect.dynamic_anchor_keyword)
            if isinstance(value, str):
                dynamic_name = value
        elif dialect.recursive_anchor_keyword is not None:
            if node.get(dialect.recursive_anchor_keyword) is True:
                dynamic_name = ""
        return AnchorMatch(plain_name=plain_name, dynamic_name=dynamic_name)

    def reference_keyword(self, dialect: Optional[Dialect]) -> str:
        assert dialect is not None
        return dialect.ref_keyword


# ---------------------------------------------------------------------------
# Built-in dialect presets
# ---------------------------------------------------------------------------

_DRAFT4_APPLICATORS: Dict[str, ApplicatorKind] = {
    "properties": ApplicatorKind.SCHEMA_MAP,
    "patternProperties": ApplicatorKind.SCHEMA_MAP,
    "definitions": ApplicatorKind.SCHEMA_MAP,
    "additionalProperties": ApplicatorKind.SINGLE_SCHEMA,
    "items": ApplicatorKind.SCHEMA_OR_SCHEMA_ARRAY,
    "additionalItems": ApplicatorKind.SINGLE_SCHEMA,
    "allOf": ApplicatorKind.SCHEMA_ARRAY,
    "anyOf": ApplicatorKind.SCHEMA_ARRAY,
    "oneOf": ApplicatorKind.SCHEMA_ARRAY,
    "not": ApplicatorKind.SINGLE_SCHEMA,
    "dependencies": ApplicatorKind.MIXED_MAP,
}

_DRAFT6_APPLICATORS: Dict[str, ApplicatorKind] = {
    **_DRAFT4_APPLICATORS,
    "propertyNames": ApplicatorKind.SINGLE_SCHEMA,
    "contains": ApplicatorKind.SINGLE_SCHEMA,
}

_DRAFT7_APPLICATORS: Dict[str, ApplicatorKind] = {
    **_DRAFT6_APPLICATORS,
    "if": ApplicatorKind.SINGLE_SCHEMA,
    "then": ApplicatorKind.SINGLE_SCHEMA,
    "else": ApplicatorKind.SINGLE_SCHEMA,
}

_DRAFT2019_09_APPLICATORS: Dict[str, ApplicatorKind] = {
    **_DRAFT7_APPLICATORS,
    "$defs": ApplicatorKind.SCHEMA_MAP,
    "dependentSchemas": ApplicatorKind.SCHEMA_MAP,
    "unevaluatedProperties": ApplicatorKind.SINGLE_SCHEMA,
    "unevaluatedItems": ApplicatorKind.SINGLE_SCHEMA,
}

_DRAFT2020_12_APPLICATORS: Dict[str, ApplicatorKind] = {
    **_DRAFT2019_09_APPLICATORS,
    "items": ApplicatorKind.SINGLE_SCHEMA,
    "prefixItems": ApplicatorKind.SCHEMA_ARRAY,
}

_OPENAPI_SCHEMA_APPLICATORS: Dict[str, ApplicatorKind] = {
    "properties": ApplicatorKind.SCHEMA_MAP,
    "additionalProperties": ApplicatorKind.SINGLE_SCHEMA,
    "items": ApplicatorKind.SINGLE_SCHEMA,
    "allOf": ApplicatorKind.SCHEMA_ARRAY,
    "anyOf": ApplicatorKind.SCHEMA_ARRAY,
    "oneOf": ApplicatorKind.SCHEMA_ARRAY,
    "not": ApplicatorKind.SINGLE_SCHEMA,
}

DRAFT_04 = Dialect(name="draft-04", id_keyword="id", applicators=_DRAFT4_APPLICATORS)

DRAFT_06 = Dialect(name="draft-06", id_keyword="$id", applicators=_DRAFT6_APPLICATORS)

DRAFT_07 = Dialect(name="draft-07", id_keyword="$id", applicators=_DRAFT7_APPLICATORS)

DRAFT_2019_09 = Dialect(
    name="2019-09",
    id_keyword="$id",
    anchor_keyword="$anchor",
    recursive_ref_keyword="$recursiveRef",
    recursive_anchor_keyword="$recursiveAnchor",
    applicators=_DRAFT2019_09_APPLICATORS,
)

DRAFT_2020_12 = Dialect(
    name="2020-12",
    id_keyword="$id",
    anchor_keyword="$anchor",
    dynamic_ref_keyword="$dynamicRef",
    dynamic_anchor_keyword="$dynamicAnchor",
    applicators=_DRAFT2020_12_APPLICATORS,
)

SWAGGER_2_0 = Dialect(
    name="swagger-2.0",
    root_context=NodeContext.STRUCTURAL,
    id_keyword=None,
    applicators=_OPENAPI_SCHEMA_APPLICATORS,
    structural_entry_keywords={
        "schema": ApplicatorKind.SINGLE_SCHEMA,
        "definitions": ApplicatorKind.SCHEMA_MAP,
    },
)

OPENAPI_3_0 = Dialect(
    name="openapi-3.0",
    root_context=NodeContext.STRUCTURAL,
    id_keyword=None,
    applicators=_OPENAPI_SCHEMA_APPLICATORS,
    structural_entry_keywords={
        "schema": ApplicatorKind.SINGLE_SCHEMA,
        "schemas": ApplicatorKind.SCHEMA_MAP,
    },
)

OPENAPI_3_1 = Dialect(
    name="openapi-3.1",
    root_context=NodeContext.STRUCTURAL,
    id_keyword="$id",
    anchor_keyword="$anchor",
    dynamic_ref_keyword="$dynamicRef",
    dynamic_anchor_keyword="$dynamicAnchor",
    applicators=_DRAFT2020_12_APPLICATORS,
    structural_entry_keywords={
        "schema": ApplicatorKind.SINGLE_SCHEMA,
        "schemas": ApplicatorKind.SCHEMA_MAP,
    },
)

ASYNCAPI_2 = Dialect(
    name="asyncapi-2",
    root_context=NodeContext.STRUCTURAL,
    id_keyword="$id",
    applicators=_DRAFT7_APPLICATORS,
    structural_entry_keywords={
        "payload": ApplicatorKind.SINGLE_SCHEMA,
        "schema": ApplicatorKind.SINGLE_SCHEMA,
        "schemas": ApplicatorKind.SCHEMA_MAP,
    },
)

ASYNCAPI_3 = Dialect(
    name="asyncapi-3",
    root_context=NodeContext.STRUCTURAL,
    id_keyword="$id",
    anchor_keyword="$anchor",
    dynamic_ref_keyword="$dynamicRef",
    dynamic_anchor_keyword="$dynamicAnchor",
    applicators=_DRAFT2020_12_APPLICATORS,
    structural_entry_keywords={
        "payload": ApplicatorKind.SINGLE_SCHEMA,
        "schema": ApplicatorKind.SINGLE_SCHEMA,
        "schemas": ApplicatorKind.SCHEMA_MAP,
    },
)

_BUILTIN_DIALECTS: Dict[str, Dialect] = {
    "draft-04": DRAFT_04,
    "draft-06": DRAFT_06,
    "draft-07": DRAFT_07,
    "2019-09": DRAFT_2019_09,
    "2020-12": DRAFT_2020_12,
    "swagger-2.0": SWAGGER_2_0,
    "openapi-2.0": SWAGGER_2_0,
    "openapi-3.0": OPENAPI_3_0,
    "openapi-3.1": OPENAPI_3_1,
    "asyncapi-2": ASYNCAPI_2,
    "asyncapi-3": ASYNCAPI_3,
}

_SCHEMA_URI_HINTS = [
    ("2020-12", DRAFT_2020_12),
    ("2019-09", DRAFT_2019_09),
    ("draft-07", DRAFT_07),
    ("draft-06", DRAFT_06),
    ("draft-04", DRAFT_04),
]


def _coerce_dialect(dialect: Optional[Union[str, Dialect]]) -> Optional[Dialect]:
    if dialect is None:
        return None
    if isinstance(dialect, Dialect):
        return dialect
    try:
        return _BUILTIN_DIALECTS[dialect]
    except KeyError:
        raise ValueError(
            f"Unknown dialect name '{dialect}'. Known dialects: {sorted(_BUILTIN_DIALECTS)}"
        ) from None


def detect_dialect(structure: Any) -> Optional[Dialect]:
    """Inspect a raw (un-wrapped) parsed document and pick a built-in `Dialect`, based on
    `$schema` / `openapi` / `swagger` / `asyncapi` root fields. Returns None if nothing was
    recognized.
    """
    if not isinstance(structure, dict):
        return None

    schema_uri = structure.get("$schema")
    if isinstance(schema_uri, str):
        for hint, dialect in _SCHEMA_URI_HINTS:
            if hint in schema_uri:
                return dialect

    openapi_version = structure.get("openapi")
    if isinstance(openapi_version, str):
        if openapi_version.startswith("3.1"):
            return OPENAPI_3_1
        if openapi_version.startswith("3.0"):
            return OPENAPI_3_0

    swagger_version = structure.get("swagger")
    if isinstance(swagger_version, str) and swagger_version.startswith("2."):
        return SWAGGER_2_0

    asyncapi_version = structure.get("asyncapi")
    if isinstance(asyncapi_version, str):
        if asyncapi_version.startswith("3."):
            return ASYNCAPI_3
        if asyncapi_version.startswith("2."):
            return ASYNCAPI_2

    return None
