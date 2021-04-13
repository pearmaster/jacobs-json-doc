
from collections import UserDict, UserList
from enum import Enum
from loader import LoaderBaseClass
from parser import Parser
from resolver import ResolverBaseClass


class RefResolutionMode(Enum):
    USE_REFERENCES_OBJECTS = 0
    RESOLVE_REFERENCES = 1


class PathReferenceResolutionError(Exception):

    def __init__(self, doc, path):
        super().__init__(f"Could not resolve path: '{path}' from {doc.uri}")

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
            if len(data) == 1 and '$ref' in data:
                dref = DocReference(data['$ref'], self.root, data.lc.line)
                return dref
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

    def resolve_references(self):
        for k, v in self.data.items():
            if isinstance(v, DocReference):
                self.data[k] = v.resolve()
            elif isinstance(v, DocObject):
                v.resolve_references()


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
    def is_ref(self):
        return True

    @property
    def reference(self):
        return self._reference

    def resolve(self):
        href, path = self._reference.split('#')
        doc = self.root
        if len(href) > 0:
            try:
                uri = self.root.resolve_uri(href)
            except:
                raise Exception(f"Could not resolve '{href}'")
            try:
                doc = self.root.get_doc(uri)
            except:
                raise Exception(f"Could not create document '{href}'")
        node = doc.get_node(path)
        return node

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

    def __init__(self, uri, resolver: ResolverBaseClass, loader: LoaderBaseClass, ref_resolution=RefResolutionMode.USE_REFERENCES_OBJECTS):
        self._ref_resolution_mode=ref_resolution
        self._uri = uri
        self._resolver = resolver
        self._loader = loader
        self.parser = Parser()
        self._doc_cache = DocumentCache(self._resolver, self._loader, self._ref_resolution_mode)
        structure = self.parser.parse_yaml(loader.load(self._uri))
        super().__init__(structure, self, 0)
        if self._ref_resolution_mode == RefResolutionMode.RESOLVE_REFERENCES:
            self.resolve_references()

    @property
    def uri(self):
        return self._uri

    def resolve_uri(self, href):
        return self._resolver.resolve(self._uri, href)

    def get_node(self, path):
        path_parts = [ p for p in path.split('/') if len(p) > 0 ]
        node = self
        for part in path_parts:
            try:
                node = node[part]
            except KeyError:
                raise PathReferenceResolutionError(self, path)
        return node

    def get_doc(self, uri):
        return self._doc_cache.get_doc(uri)



class DocumentCache(object):

    def __init__(self, resolver, loader, ref_resolution_mode):
        self._cache = {}
        self._resolver = resolver
        self._loader = loader
        self._ref_resolution_mode = ref_resolution_mode
    
    def get_doc(self, uri):
        if uri not in self._cache:
            doc = Document(uri, self._resolver, self._loader, ref_resolution=self._ref_resolution_mode)
            self._cache[uri] = doc
        return self._cache[uri]

# TODO: DocumentCache should be a singleton (only ever one instance)
# TODO: detect circular references
# TODO: better exception raising