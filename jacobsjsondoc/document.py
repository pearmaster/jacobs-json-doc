

import json
from typing import Optional

from .loader import LoaderBaseClass, FilesystemLoader
from .parser import Parser
from .reference import ReferenceDictionary, JsonAnchor
from .options import ParseOptions, RefResolutionMode


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
            dollar_id = JsonAnchor.empty()

        if isinstance(data, dict):
            if self.root._dollar_ref_token in data and isinstance(data[self.root._dollar_ref_token], str):
                dref = DocReference(data[self.root._dollar_ref_token], dollar_id, self.root, data.lc.line)
                return dref
            dobj = DocObject(data, self.root, data.lc.line, dollar_id=dollar_id)
            return dobj
        elif isinstance(data, list):
            da = DocArray(data, self.root, data.lc.line, dollar_id=dollar_id)
            return da
        else:
            if idx is not None:
                if isinstance(parent, dict):
                    dv = DocValue.factory(data, self.root, parent.lc.value(idx)[0])
                    if dv is not None and not isinstance(dv, bool):
                        dv.set_key(idx, parent.lc.key(idx)[0])
                    return dv
                elif isinstance(parent, list):
                    dv = DocValue.factory(data, self.root, parent.lc.item(idx)[0])
                    if dv is not None and not isinstance(dv, bool):
                        dv.set_key(idx, parent.lc.item(idx)[0])
                    return dv
            else:
                return DocValue(data, self.root, line=None)


class DocContainer(DocElement):

    def __init__(self, doc_root, line: int, dollar_id=None):
        if dollar_id is None:
            dollar_id = JsonAnchor.empty()
        self._dollar_id = dollar_id
        super().__init__(doc_root, line)


class DocObject(DocContainer, dict):

    def __init__(self, data: dict, doc_root, line: int, dollar_id=None):
        super().__init__(doc_root, line, dollar_id)
        if self.root._dollar_id_token in data:
            self._dollar_id.change_to(data[self.root._dollar_id_token])
            self.root._ref_dictionary.put(self._dollar_id, self)
        for k, v in data.items():

            # There may be certain structures were we don't want to parse $id or $ref.
            # In JSON-Schema, these include elements under `enum` and `const`
            # Here we detect those cases and set the tokens to None so we don't
            # detect them.
            if k in self.root._parse_options.exclude_dollar_id_parse:
                self.root._dollar_id_token = None
            if k in self.root._parse_options.exclude_dollar_ref_parse:
                self.root._dollar_ref_token = None

            self[k] = self.construct(data=v, parent=data, idx=k, dollar_id=self._dollar_id.copy())

            # Now, restore the $id and $ref parsing tokens
            if k in self.root._parse_options.exclude_dollar_id_parse:
                self.root._dollar_id_token = self.root._parse_options.dollar_id_token
            if k in self.root._parse_options.exclude_dollar_ref_parse:
                self.root._dollar_ref_token = self.root._parse_options.dollar_ref_token

    def resolve_references(self):
        for k, v in self.items():
            if isinstance(v, DocReference):
                self[k] = v.resolve()
            elif isinstance(v, DocObject):
                v.resolve_references()


class DocArray(DocContainer, list):

    def __init__(self, data: list, doc_root, line: int, dollar_id=None):
        super().__init__(doc_root, line, dollar_id)
        for i, v in enumerate(data):
            self.append(self.construct(data=v, parent=data, idx=i, dollar_id=self._dollar_id.copy()))


class DocReference(DocElement):

    def __init__(self, reference:str, dollar_id:Optional[JsonAnchor], doc_root, line:int):
        super().__init__(doc_root, line)
        self._reference = reference
        self._dollar_id = dollar_id.copy()
        if self._dollar_id is None:
            self._dollar_id = JsonAnchor.empty()

    @property
    def reference(self):
        return self._reference

    def resolve(self):
        try:
            js_anchor = self._dollar_id.copy().change_to(self._reference)
            node = self.root._ref_dictionary.get(js_anchor)
            return node
        except:
            pass
        reference_parts = self._reference.split('#')
        if len(reference_parts) == 2:
            href, path = reference_parts
        elif len(reference_parts) == 1:
            href = reference_parts[0]
            path = ""
        doc = self.root
        if len(href) > 0:
            doc = self.root.get_doc(href)
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
        if isinstance(value, bool):
            return value
        elif isinstance(value, int):
            return DocInteger(value, doc_root, line)
        elif isinstance(value, float):
            return DocFloat(value, doc_root, line)
        elif isinstance(value, str):
            return DocString(value, doc_root, line)
        elif value is None:
            return None
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
        # This is stupid and needs to be fixed.
        # It is here to correctly load a poop emoji found
        # in the minLength.json JSON-Schema test data.
        new_value = json.loads(json.dumps(value))
        new_len = len(new_value)
        ds = str.__new__(DocString, new_value)
        ds.__init__(new_value, doc_root, line)
        return ds

    def __init__(self, value: str, doc_root, line: int):
        DocValue.__init__(self, value, doc_root, line)

class Document:
    pass

def create_document(uri, loader: Optional[LoaderBaseClass]=None, options: Optional[ParseOptions]=None):
    if loader is None:
        loader = FilesystemLoader()
    if options is None:
        options = ParseOptions()
    parser = Parser()
    structure = parser.parse_yaml(loader.load(uri))
    base_class = DocObject
    if isinstance(structure, list):
        base_class = DocArray
    elif isinstance(structure, dict) and options.dollar_ref_token in structure and isinstance(structure[options.dollar_ref_token], str):
        uri = structure[options.dollar_ref_token]
        fragment = None
        if '#' in uri:
            uri, fragment = uri.split('#')
        doc = create_document(uri, loader, options)
        if fragment is not None:
            doc = doc.get_node(fragment)
        return doc
    class DocumentRoot(base_class, Document):

        def __init__(self, uri, loader: LoaderBaseClass, options: ParseOptions):
            self._dollar_id_token = options.dollar_id_token
            self._dollar_ref_token = options.dollar_ref_token
            self._ref_resolution_mode = options.ref_resolution_mode
            self._parse_options = options
            self._uri = uri
            self._loader = loader
            self.parser = Parser()
            self._doc_cache = RemoteDocumentCache(self._loader, self._parse_options)
            structure = self.parser.parse_yaml(loader.load(self._uri))
            self._ref_dictionary = ReferenceDictionary()
            new_dollar_id = JsonAnchor.empty()
            if self._dollar_id_token in structure:
                uri = structure[self._dollar_id_token]
                new_dollar_id = JsonAnchor.from_string(uri)
                self._ref_dictionary.put(new_dollar_id, self)
            super().__init__(structure, self, 0, dollar_id=new_dollar_id)
            if self._ref_resolution_mode == RefResolutionMode.RESOLVE_REFERENCES:
                self.resolve_references()

        @property
        def uri(self):
            return self._uri

        @staticmethod
        def _replace_ref_escapes(ref_part:str) -> str:
            replacements = [
                ("~0", "~"),
                ("~1", "/"),
                ("%25", "%"),
                ("%22", '"'),
            ]
            ret = ref_part
            for rep in replacements:
                ret = ret.replace(*rep)
            return ret

        def get_node(self, fragment):
            fragment_parts = [ p for p in fragment.split('/') if len(p) > 0 ]
            node = self
            for part in fragment_parts:
                if part.isnumeric() and isinstance(node, list):
                    node = node[int(part)]
                    continue
                try:
                    node = node[self._replace_ref_escapes(part)]
                except KeyError:
                    raise PathReferenceResolutionError(self, fragment)
                except TypeError:
                    raise PathReferenceResolutionError(self, fragment)
            return node

        def get_doc(self, uri):
            return self._doc_cache.get_doc(uri)

    return DocumentRoot(uri, loader, options)


class RemoteDocumentCache(object):
    _cache = {}
    _loading = set()

    def __init__(self,  loader, options):
        self._loader = loader
        self._parse_options = options

    def get_doc(self, uri):
        if uri in self._loading:
            raise CircularDependencyError(uri)
        if uri not in self._cache:
            self._loading.add(uri)
            doc = create_document(uri, self._loader, self._parse_options)
            self._cache[uri] = doc
            self._loading.remove(uri)
        return self._cache[uri]
