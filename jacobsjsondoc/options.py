
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
        self.exclude_dollar_id_parse:List[str] = ["const", "enum"]
        self.exclude_dollar_ref_parse:List[str] = ["const", "enum"]
        self.should_stop_dollar_id_parse:Optional[Callable] = self._should_stop_dollar_id_parse

    def _should_stop_dollar_id_parse(self, parent, key) -> bool:
        recognized = [
            "properties", 
            "allOf", 
            "anyOf", 
            "not", 
            "oneOf", 
            "items", 
            "dependencies",
            "if", "else", "then",
            "additionalProperties",
            None
        ]
        if key in self.exclude_dollar_id_parse:
            return True
        if key not in recognized and hasattr(parent, "index") and parent.index not in recognized:
            return True
        return False
