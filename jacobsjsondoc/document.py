
from collections import UserDict, UserList
from enum import Enum
from .loader import LoaderBaseClass
from .parser import Parser
from .resolver import ResolverBaseClass
from .reference import ReferenceDictionary, JsonReference

class RefResolutionMode(Enum):
    USE_REFERENCES_OBJECTS = 0
    RESOLVE_REFERENCES = 1


class ReferenceResolutionError(Exception):
    pass

class PathReferenceResolutionError(ReferenceResolutionError):

    def __init__(self, doc, path):
        super().__init__(f"Could not resolve path: '{path}' from {doc.uri}")


class CircularDependencyError(ReferenceResolutionError):
    def __init__(self, uri):
        super().__init__(f"Circular dependency detected when trying to load '{uri}' a second time")


class DocElement:

    def __init__(self, doc_root, line: int):
        self._line = line
        self._doc_root = doc_root

    @property
    def line(self) -> int:
        return self._line

    @line.setter
    def line(self, value: int):
        self._line = value

    @property
    def uri_line(self):
        return f"{self.root.uri}:{self.line}"

    @property
    def root(self):
        return self._doc_root

    def construct(self, data, parent, idx=None, dollar_id=None):
        if dollar_id is None:
            dollar_id = JsonReference.empty()

        if isinstance(data, dict):
            if len(data) == 1 and '$ref' in data:
                dref = DocReference(data['$ref'], self.root, data.lc.line)
                return dref
            dobj = DocObject(data, self.root, data.lc.line, dollar_id=dollar_id)
            #for k, v in data.items():
            #    dobj[k] = self.construct(data=v, parent=data, idx=k, dollar_id=dollar_id)
            return dobj
        elif isinstance(data, list):
            da = DocArray(data, self.root, data.lc.line, dollar_id=dollar_id)
            #for i, v in enumerate(data):
            #    da.append(self.construct(data=v, parent=data, idx=i, dollar_id=dollar_id))
            return da
        else:
            if idx is not None:
                if isinstance(parent, dict):
                    dv = DocValue.factory(data, self.root, parent.lc.value(idx)[0])
                    dv.set_key(idx, parent.lc.key(idx)[0])
                    return dv
                elif isinstance(parent, list):
                    dv = DocValue(data, self.root, parent.lc.item(idx)[0])
                    dv.set_key(idx, parent.lc.item(idx)[0])
                    return dv
            else:
                return DocValue(data, self.root, line=None)


class DocContainer(DocElement):

    def __init__(self, doc_root, line: int, dollar_id=None):
        if dollar_id is None:
            dollar_id = JsonReference.empty()
        self._dollar_id = dollar_id
        super().__init__(doc_root, line)


class DocObject(DocContainer, UserDict):
    
    def __init__(self, data: dict, doc_root, line: int, dollar_id=None):
        super().__init__(doc_root, line, dollar_id)
        if self.root._dollar_id_token in data:
            self._dollar_id.change_to(data[self.root._dollar_id_token])
            self.root._ref_dictionary.put(self._dollar_id, self)
        self.data = {}
        for k, v in data.items():
            self.data[k] = self.construct(data=v, parent=data, idx=k, dollar_id=self._dollar_id.copy())

    def resolve_references(self):
        for k, v in self.data.items():
            if isinstance(v, DocReference):
                self.data[k] = v.resolve()
            elif isinstance(v, DocObject):
                v.resolve_references()


class DocArray(DocContainer, UserList):

    def __init__(self, data: list, doc_root, line: int, dollar_id=None):
        super().__init__(doc_root, line, dollar_id)
        self.data = []
        for i, v in enumerate(data):
            self.data.append(self.construct(data=v, parent=data, idx=i, dollar_id=self._dollar_id.copy()))


class DocReference(DocElement):

    def __init__(self, reference, doc_root, line):
        super().__init__(doc_root, line)
        self._reference = reference

    @property
    def reference(self):
        return self._reference

    def resolve(self):
        href, path = self._reference.split('#')
        doc = self.root
        if len(href) > 0:
            uri = self.root.resolve_uri(href)
            doc = self.root.get_doc(uri)
        node = doc.get_node(path)
        return node

class DocValue(DocElement):

    def __init__(self, value, doc_root, line: int):
        DocElement.__init__(self, doc_root, line)
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

    @staticmethod
    def factory(value, doc_root, line: int):
        if isinstance(value, int):
            return DocInteger(value, doc_root, line)
        elif isinstance(value, float):
            return DocFloat(value, doc_root, line)
        elif isinstance(value, str):
            return DocString(value, doc_root, line)
        elif isinstance(value, bool):
            return DocBoolean(value, doc_root, line)
        elif value is None:
            return DocNull(None, doc_root, line)
        return DocValue(value, doc_root, line)


class DocInteger(DocValue, int):

    def __new__(cls, value: int, doc_root, line: int):
        di = int.__new__(DocInteger, value)
        di.__init__(value, doc_root, line)
        return di

    def __init__(self, value: int, doc_root, line: int):
        DocValue.__init__(self, value, doc_root, line)


class DocFloat(DocValue, float):

    def __new__(cls, value: float, doc_root, line: int):
        df = float.__new__(DocFloat, value)
        df.__init__(value, doc_root, line)
        return df

    def __init__(self, value: float, doc_root, line: int):
        DocValue.__init__(self, value, doc_root, line)


class DocString(DocValue, str):

    def __new__(cls, value: str, doc_root, line: int):
        ds = str.__new__(DocString, value)
        ds.__init__(value, doc_root, line)
        return ds

    def __init__(self, value: str, doc_root, line: int):
        DocValue.__init__(self, value, doc_root, line)


class DocBoolean(DocValue, int):

    def __new__(cls, value: bool, doc_root, line: int):
        db = bool.__new__(DocString, value)
        db.__init__(value, doc_root, line)
        return db

    def __init__(self, value: bool, doc_root, line: int):
        DocValue.__init__(self, value, doc_root, line)


class DocNull(DocValue):
    pass


def create_document(uri, resolver: ResolverBaseClass, loader: LoaderBaseClass, ref_resolution=RefResolutionMode.USE_REFERENCES_OBJECTS, dollar_id_token="$id"):

    parser = Parser()
    structure = parser.parse_yaml(loader.load(uri))
    base_class = DocObject
    if isinstance(structure, list):
        base_class = DocArray

    class Document(base_class):

        def __init__(self, uri, resolver: ResolverBaseClass, loader: LoaderBaseClass, ref_resolution=RefResolutionMode.USE_REFERENCES_OBJECTS, dollar_id_token="$id"):
            self._dollar_id_token = dollar_id_token
            self._ref_resolution_mode=ref_resolution
            self._uri = uri
            self._resolver = resolver
            self._loader = loader
            self.parser = Parser()
            self._doc_cache = DocumentCache(self._resolver, self._loader, self._ref_resolution_mode)
            structure = self.parser.parse_yaml(loader.load(self._uri))
            self._ref_dictionary = ReferenceDictionary()
            new_dollar_id = JsonReference.empty()
            if self._dollar_id_token in structure:
                uri = structure[self._dollar_id_token]
                new_dollar_id = JsonReference.from_string(uri)
                self._ref_dictionary.put(new_dollar_id, self)
            super().__init__(structure, self, 0, dollar_id=new_dollar_id)
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

    return Document(uri, resolver, loader, ref_resolution, dollar_id_token)


class DocumentCache(object):
    _cache = {}
    _loading = set()

    def __init__(self, resolver, loader, ref_resolution_mode):
        self._resolver = resolver
        self._loader = loader
        self._ref_resolution_mode = ref_resolution_mode
    
    def get_doc(self, uri):
        if uri in self._loading:
            raise CircularDependencyError(uri)
        if uri not in self._cache:
            self._loading.add(uri)
            doc = create_document(uri, self._resolver, self._loader, ref_resolution=self._ref_resolution_mode)
            self._cache[uri] = doc
            self._loading.remove(uri)
        return self._cache[uri]
