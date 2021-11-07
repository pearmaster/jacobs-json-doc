
from typing import List

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
