
from typing import Optional

from enum import Enum

class RefResolutionMode(Enum):
    USE_REFERENCES_OBJECTS = 0
    RESOLVE_REFERENCES = 1
    RESOLVE_WHEN_REQUIRED = 2


class ParseOptions:

    def __init__(self):
        self.ref_resolution_mode:RefResolutionMode = RefResolutionMode.USE_REFERENCES_OBJECTS
        self.dollar_id_token:str = "$id"
        self.dollar_ref_token:str = "$ref"

    def get_base_uri(self, parent, node):
        if self.dollar_id_token in node:
            if not isinstance(node[self.dollar_id_token], str):
                return None
            return node[self.dollar_id_token]
        return None

    def get_reference(self, parent, idx, node):
        if self.dollar_ref_token in node:
            if not isinstance(node[self.dollar_ref_token], str):
                return None
            return node[self.dollar_ref_token]
        return None


class JsonSchemaParseOptions(ParseOptions):

    def _is_unknown_keyword_inside_schema(self, parent) -> Optional[int]:
        keywords_for_schemas = [
            "not",
            "additionalProperties",
            "dependencies",
            "dependentSchemas",
            "if",
            "then",
            "else",
        ]
        parent_node = parent
        iterations = 0
        while parent_node is not None:
            iterations += 1
            if iterations == 10:
                break
            grandparent = parent_node._pointers.parent
            if grandparent is None:
                break
            if grandparent.index in keywords_for_schemas:
                if parent_node.index not in keywords_for_schemas:
                    return iterations
            parent_node = parent_node._pointers.parent
        return None

    def _is_inside_properties(self, parent, prop_names:list) -> Optional[int]:
        parent_node = parent
        iterations = 0
        while parent_node is not None:
            iterations += 1
            if iterations == 100:
                raise Exception("Too Many Interations")
            if parent_node.index in prop_names:
                return iterations
            parent_node = parent_node._pointers.parent
        return None

    def _is_inside_enum(self, parent) -> Optional[int]:
        return self._is_inside_properties(parent, prop_names=["enum", "const"])

    def _is_inside_definitions(self, parent) -> Optional[int]:
        return self._is_inside_properties(parent, prop_names=["definitions"])

    def get_reference(self, parent, idx, node):
        if self.dollar_ref_token in node:
            if not isinstance(node[self.dollar_ref_token], str):
                return None
            if self._is_inside_enum(parent):
                return None
            return node[self.dollar_ref_token]
        return None

    def get_base_uri(self, parent, node):
        if self.dollar_id_token in node:
            if not isinstance(node[self.dollar_id_token], str):
                return None
            base_uri = node[self.dollar_id_token]
            if self._is_inside_enum(parent):
                return None
            steps_to_definitions = self._is_inside_definitions(parent)
            steps_to_unknown = self._is_unknown_keyword_inside_schema(parent)
            if steps_to_unknown is None:
                return base_uri
            if steps_to_definitions is None:
                return None
            if steps_to_definitions <= steps_to_unknown:
                return base_uri
        return None