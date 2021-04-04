
from collections import UserDict, UserList
from enum import Enum
from loader import LoaderBaseClass
from parser import Parser
from resolver import ResolverBaseClass


class ParseMode(Enum):
    DEFAULT = 0


class DocElement:

    def __init__(self, doc_root: DocArray, line: int):
        self._line = line
        self._doc_root = doc_root

    @property
    def line(self) -> int:
        return self._line

    @line.setter
    def line(self, value: int):
        self._line = value

    @property
    def root(self) -> Document:
        return self._doc_root

    def convert(self, data, parent, idx=None):
        if isinstance(data, dict):
            return DocObject(data, self.root, data.lc.line)
        elif isinstance(data, list):
            return DocArray(data, self.root, data.lc.line)
        else:
            if idx is not None:
                if isinstance(parent, dict):
                    dv = DocValue(data, self.root, parent.lc.value(key))
                    dv.set_key(key, parent.lc.key(key))
                    return dv
                elif isinstance(parent, list):
                    dv = DocValue(data, self.root, parent.lc.)
            if idx is not None:
                pass


class DocObject(DocElement, UserDict):
    
    def __init__(self, data: dict, doc_root: Document, line: int):
        super().__init__(doc_root, line)
        for k, v in data.items():
            if 


class DocArray(DocElement, UserList):

    def __init__(self, data: list, doc_root: Document, line: int):
        super().__init__(doc_root, line)
        self.data = data


class DocValue(DocElement):

    def __init__(self, value, doc_root: Document, line: int):
        super().__init__(doc_root, line)
        self.data = value
        self.key = None
        self.key_line = None

    @property
    def value(self):
        return self.data

    def set_key(self, key_name, key_line):
        self.key = key_name
        self.key_line = key_line


class Document(DocObject:

    def __init__(self, uri, resolver: ResolverBaseClass, loader: LoaderBaseClass, parse_mode: ParseMode=ParseMode.DEFAULT):
        self._uri = uri
        self._resolver = resolver
        self._loader = loader
        self.parse_mode = parse_mode
        super().__init__(loader.Load(self._uri))