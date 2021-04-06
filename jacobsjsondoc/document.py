
from collections import UserDict, UserList
from enum import Enum
from loader import LoaderBaseClass
from parser import Parser
from resolver import ResolverBaseClass


class DocElement:

    def __init__(self, doc_root, line: int):
        self._line = line
        self._doc_root = doc_root
        self._is_ref = False

    @property
    def line(self) -> int:
        return self._line

    @line.setter
    def line(self, value: int):
        self._line = value

    @property
    def root(self):
        return self._doc_root

    @property
    def is_ref(self):
        self._is_ref

    def construct(self, data, parent, idx=None):
        if isinstance(data, dict):
            dobj = DocObject(data, self.root, data.lc.line)
            for k, v in data.items():
                dobj[k] = self.construct(v, data, k)
            return dobj
        elif isinstance(data, list):
            da = DocArray(data, self.root, data.lc.line)
            for i, v in enumerate(data):
                da.append(self.construct(v, data, i))
            return da
        else:
            if idx is not None:
                if isinstance(parent, dict):
                    dv = DocValue(data, self.root, parent.lc.value(idx)[0])
                    dv.set_key(idx, parent.lc.key(idx)[0])
                    return dv
                elif isinstance(parent, list):
                    dv = DocValue(data, self.root, parent.lc.item(idx)[0])
                    dv.set_key(idx, parent.lc.item(idx)[0])
                    return dv
            else:
                return DocValue(data, self.root, line=None)


class DocObject(DocElement, UserDict):
    
    def __init__(self, data: dict, doc_root, line: int):
        super().__init__(doc_root, line)
        self.data = {}
        for k, v in data.items():
            self.data[k] = self.construct(v, data, k)


class DocArray(DocElement, UserList):

    def __init__(self, data: list, doc_root, line: int):
        super().__init__(doc_root, line)
        self.data = []
        for i, v in enumerate(data):
            self.data.append(self.construct(v, data, i))


class DocReference(DocElement):

    def __init__(self, reference, doc_root, line):
        super().__init__(doc_root, line)
        self._reference = reference

    @property
    def is_reference(self):
        return True


class DocValue(DocElement):

    def __init__(self, value, doc_root, line: int):
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

    def __repr__(self):
        if isinstance(self.data, str):
            return f'"{self.data}"'
        return str(self.data)


class Document(DocObject):

    def __init__(self, uri, resolver: ResolverBaseClass, loader: LoaderBaseClass):
        self._uri = uri
        self._resolver = resolver
        self._loader = loader
        self.parser = Parser()
        structure = self.parser.parse_yaml(loader.load(self._uri))
        super().__init__(structure, self, 0)

class DocumentCache(object):

    def __init__(self, resolver, loader):
        self._cache = {}
        self._resolver = resolver
        self._loader = loader
    
    def get_doc(self, uri):
        if uri not in self._cache:
            data = self._loader.load(uri)
            doc = Document(data, self._resolver, self._loader)
            self._cache[uri] = doc
        return self._cache[uri]
