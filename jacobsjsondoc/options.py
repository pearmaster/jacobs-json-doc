
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

    def has_new_base_uri(self, parent, node):
        if self.dollar_id_token in node:
            if not isinstance(node[self.dollar_id_token], str):
                return False
            if parent._pointers.idx in ["enum"]:
                return False
            return True
        return False

    def get_reference(self, parent, idx, node):
        if self.dollar_ref_token in node:
            if not isinstance(node[self.dollar_ref_token], str):
                return None
            if idx in ["properties", "enum"]:
                return None
            return node[self.dollar_ref_token]
        return None