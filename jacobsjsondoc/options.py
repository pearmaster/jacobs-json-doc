
from typing import List, Callable

from enum import Enum

class RefResolutionMode(Enum):
    USE_REFERENCES_OBJECTS = 0
    RESOLVE_REFERENCES = 1


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

class JsonSchemaDraft4ParseOptions(ParseOptions):

    def _is_unknown_keyword_inside_schema(self, parent):
        return False

    def _is_inside_enum(self, parent):
        parent_node = parent
        maximum_iterations = 200
        while parent_node is not None:
            maximum_iterations -= 1
            if maximum_iterations == 0:
                raise Exception("Too Many Interations")
            if parent_node.index == "enum" or parent_node.index == "const":
                return True
            parent_node = parent_node._pointers.parent
        return False

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
            if self._is_inside_enum(parent):
                return None
            if self._is_unknown_keyword_inside_schema(parent):
                return None
            return node[self.dollar_id_token]
        return None

class JsonSchemaDraft6ParseOptions(JsonSchemaDraft4ParseOptions):

    def _is_unknown_keyword_inside_schema(self, parent):
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
        maximum_iterations = 5
        while parent_node is not None:
            maximum_iterations -= 1
            if maximum_iterations == 0:
                break
            grandparent = parent_node._pointers.parent
            if grandparent is None:
                break
            if grandparent.index in keywords_for_schemas:
                if parent_node.index not in keywords_for_schemas:
                    return True
            parent_node = parent_node._pointers.parent
        return False
