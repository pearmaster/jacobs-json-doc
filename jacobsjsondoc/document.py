
from __future__ import annotations
import json
from typing import Optional, Union, Set, Dict, Any

from .loader import LoaderBaseClass, FilesystemLoader
from .parser import Parser
from .reference import JsonPointer
from .options import ParseOptions, RefResolutionMode

IndexKey = Union[str, int]
Uri = str

class ReferenceResolutionError(Exception):
    pass

class PathReferenceResolutionError(ReferenceResolutionError):

    def __init__(self, doc, path):
        super().__init__(f"Could not resolve fragment: '{path}' from {doc}")


class CircularDependencyError(ReferenceResolutionError):
    def __init__(self, uri):
        super().__init__(f"Circular dependency detected when trying to load '{uri}' a second time")


class UnableToLoadDocument(Exception):
    pass

class IncompletePointers:

    def __init__(self, parents_pointer: ElementPointers, idx, line=None):
        self._parents_pointer = parents_pointer
        self._idx = idx
        self._line = line

    @property
    def dollar_ref_token(self):
        return self._parents_pointer.controller.options.dollar_ref_token

    def complete(self, node: DocElement) -> ElementPointers:
        new_ptr = self._parents_pointer.child(self._idx, node)
        if self._line:
            new_ptr.line = self._line
        return new_ptr

class ElementPointers:

    def __init__(self, retrieval_uri: Union[JsonPointer, str], node: DocElement, controller: ParseController):
        if isinstance(retrieval_uri, JsonPointer):
            self.retrieval_uri = retrieval_uri
        else:
            self.retrieval_uri = JsonPointer.from_uri_string(retrieval_uri)
        self.controller = controller
        self.schema_root = node
        self.document_root = node
        self.me = node
        self.parent = None
        self.idx = None
        self.line = None
        self.base_uri = self.retrieval_uri.copy()

    @property
    def dollar_ref_token(self):
        return self.controller.options.dollar_ref_token

    @property
    def dollar_id_token(self):
        return self.controller.options.dollar_id_token

    @property
    def ref_resolution_mode(self):
        return self.controller.options.ref_resolution_mode

    def update_base_uri(self, uri: str):
        self.base_uri.to(uri)
        self.schema_root = self.me

    def child(self, idx, node):
        new_ptr = ElementPointers(self.retrieval_uri.copy(), node, self.controller)
        if self.schema_root is not None:
            new_ptr.schema_root = self.schema_root
        if self.document_root is not None:
            new_ptr.document_root = self.document_root
        new_ptr.base_uri = self.base_uri.copy()
        new_ptr.parent = self.me
        new_ptr.idx = idx
        return new_ptr


class DocElement:

    def __init__(self, pointers: IncompletePointers):
        self._pointers = pointers.complete(self)

    @property
    def line(self) -> int:
        return self._pointers.line

    @property
    def uri_line(self):
        line = ""
        if self.line is not None:
            line = f":{self.line}"
        return f"{self._pointers.retrieval_uri}{line}"

    @property
    def index(self):
        return self._pointers.idx

    @property
    def base_uri(self):
        return self._pointers.base_uri

    @staticmethod
    def construct(data, incomplete_pointers: IncompletePointers):
        """ This is a factory for new elements inheriting from DocElement, based on the
        data that is passed in.

        @param pointers that should be assigned to the created object.
        """

        if isinstance(data, dict):
            ref = incomplete_pointers._parents_pointer.controller.options.get_reference(incomplete_pointers._parents_pointer.me, incomplete_pointers._idx, data)
            if ref is not None:
                doc_ref = DocReference(ref, incomplete_pointers)
                return doc_ref
            doc_obj = DocObject(data, incomplete_pointers)
            return doc_obj
        elif isinstance(data, list):
            doc_arr = DocArray(data, incomplete_pointers)
            return doc_arr
        else: # Values
            doc_val = DocValue.factory(data, incomplete_pointers)
            return doc_val


class DocContainer(DocElement):

    def __init__(self, pointers: IncompletePointers):
        super().__init__(pointers)


class DocObject(DocContainer, dict):

    def __init__(self, data: dict, pointers: IncompletePointers):
        super().__init__(pointers)

        new_base_uri = self._pointers.controller.options.get_base_uri(self, data)
        if new_base_uri:
            self._pointers.update_base_uri(new_base_uri)
            self._pointers.controller.add_document(self._pointers.base_uri, self)

        for data_key, data_value in data.items():
            line, _ = data.lc.value(data_key)
            inc_ptrs = IncompletePointers(self._pointers, data_key, line)
            if len(data) > 1 and self._pointers.controller.options.ref_resolution_mode == RefResolutionMode.RESOLVE_WHEN_REQUIRED and data_key == self._pointers.controller.options.dollar_ref_token:
                dref = DocReference(data_value, inc_ptrs)
                dobj = dref.resolve()
                if not isinstance(dobj, DocObject):
                    raise ReferenceResolutionError(f"In the context of '{self._pointers.controller.options.dollar_ref_token}' appearing as a property in an object, it must resove to an object")
                for dobj_key, dobj_value in dobj.items():
                    self[dobj_key] = dobj_value
            else:
                self[data_key] = self.construct(data_value, inc_ptrs)

    def resolve_references(self):
        for k, v in self.items():
            if isinstance(v, DocReference):
                while isinstance(v, DocReference):
                    v = v.resolve()
                self[k] = v
            elif isinstance(v, DocObject):
                v.resolve_references()

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

    def has_node(self, fragment):
        try:
            self.get_node(fragment)
        except PathReferenceResolutionError:
            return False
        else:
            return True

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

class DocArray(DocContainer, list):

    def __init__(self, data: list, pointers: IncompletePointers):
        super().__init__(pointers)
        for list_index, data_value in enumerate(data):
            line, _ = data.lc.data[list_index]
            inc_ptrs = IncompletePointers(self._pointers, list_index, line)
            self.append(self.construct(data_value, inc_ptrs))


class DocReference(DocElement):

    def __init__(self, reference: str, pointers: IncompletePointers):
        super().__init__(pointers)
        self._reference = reference

    @property
    def reference(self):
        return self._reference

    def resolve(self):
        js_ptr = self._pointers.base_uri.copy().to(self._reference)
        try:
            if js_ptr.uri == self._pointers.schema_root.base_uri and self._pointers.schema_root.has_node(js_ptr.fragment):
                doc = self._pointers.schema_root
                node = doc._pointers.schema_root.get_node(js_ptr.fragment)
            else:
                node = self._pointers.controller.get_document(js_ptr)
        except CircularDependencyError:
            raise
        except UnableToLoadDocument:
            raise
        except:
            doc = self._pointers.schema_root
            node = doc._pointers.schema_root.get_node(js_ptr.fragment)
        return node

    def __repr__(self) -> str:
        return f"<DocReference {self._reference}>"

class DocValue(DocElement):

    def __init__(self, value, pointers: IncompletePointers):
        DocElement.__init__(self, pointers)
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
    def factory(value, pointers: IncompletePointers):
        if isinstance(value, bool):
            return value
        elif isinstance(value, int):
            return DocInteger(value, pointers)
        elif isinstance(value, float):
            return DocFloat(value, pointers)
        elif isinstance(value, str):
            return DocString(value, pointers)
        elif value is None:
            return None
        return DocValue(value, pointers)

class DocInteger(DocValue, int):

    def __new__(cls, value: int, pointers: IncompletePointers):
        di = int.__new__(DocInteger, value)
        di.__init__(value, pointers)
        return di

    def __init__(self, value: int, pointers: IncompletePointers):
        DocValue.__init__(self, value, pointers)


class DocFloat(DocValue, float):

    def __new__(cls, value: float, pointers: IncompletePointers):
        df = float.__new__(DocFloat, value)
        df.__init__(value, pointers)
        return df

    def __init__(self, value: float, pointers: IncompletePointers):
        DocValue.__init__(self, value, pointers)


class DocString(DocValue, str):

    def __new__(cls, value: str, pointers: IncompletePointers):
        # This is stupid and needs to be fixed.
        # It is here to correctly load a poop emoji found
        # in the minLength.json JSON-Schema test data.
        new_value = json.loads(json.dumps(value))
        ds = str.__new__(DocString, new_value)
        ds.__init__(new_value, pointers)
        return ds

    def __init__(self, value: str, pointers: IncompletePointers):
        DocValue.__init__(self, value, pointers)

class Document:
    """ This is a base class for DocumentRoot, which is not directly accessible since we dynamically
    assign its inheritance.  The `Document` type can be used in annotations.
    """
    pass



class ParseController:

    def __init__(self, loader: Optional[LoaderBaseClass]=None, options: Optional[ParseOptions]=None):
        self.loader = loader
        if self.loader is None:
            self.loader = FilesystemLoader()
        self.options = options
        if self.options is None:
            self.options = ParseOptions()
        self.parser = Parser()

        self._document_structure_cache: Dict[Uri, Any] = dict()
        self._document_cache: Dict[Uri, Document] = dict()
        self._loading: Set[Uri] = set()

    def add_document(self, uri: Union[JsonPointer, str], doc: DocObject):
        if isinstance(uri, str):
            self._document_cache[uri] = doc
        else:
            self._document_cache[repr(uri)] = doc

    def get_document_structure(self, uri: Union[JsonPointer, Uri]):
        if isinstance(uri, JsonPointer):
            uri = uri.uri
        if uri in self._document_structure_cache:
            return self._document_structure_cache[uri]
        try:
            json_text = self.loader.load(uri)
        except:
            raise UnableToLoadDocument(f"Could not load '{uri}'")
        structure = self.parser.parse_yaml(json_text)
        self._document_structure_cache[uri] = structure
        return structure

    def get_document(self, doc_uri: Union[JsonPointer, Uri]):
        ptr = doc_uri
        if not isinstance(ptr, JsonPointer):
            ptr = JsonPointer.from_uri_string(doc_uri)
        uri = ptr.uri
        if ptr.as_string() in self._loading:
            raise CircularDependencyError(ptr.as_string())
        if ptr.as_string() in self._document_cache:
            doc = self._document_cache[ptr.as_string()]
            return doc
        if ptr.uri in self._document_cache:
            doc = self._document_cache[ptr.uri]
            if ptr.fragment:
                doc = doc.get_node(ptr.fragment)
            return doc
        self._loading.add(ptr.as_string())
        doc = create_document(uri, controller=self)
        self.add_document(uri, doc)
        self._loading.remove(ptr.as_string())
        if ptr.fragment:
            doc = doc.get_node(ptr.fragment)
        return doc


def create_document(uri, loader: Optional[LoaderBaseClass]=None, options: Optional[ParseOptions]=None, controller: Optional[ParseController]=None):

    if controller is None:
        controller = ParseController(loader, options)
    structure = controller.get_document_structure(uri)

    initial_pointers = ElementPointers(uri, None, controller)
    
    root_pointers = IncompletePointers(initial_pointers, None, line=0)

    base_class = DocObject
    if isinstance(structure, list):
        base_class = DocArray
    elif isinstance(structure, bool):
        return structure
    elif isinstance(structure, int):
        base_class = DocInteger
    elif isinstance(structure, float):
        base_class = DocFloat
    elif isinstance(structure, str):
        base_class = DocString
    elif isinstance(structure, dict):
        if initial_pointers.dollar_ref_token in structure:
            if len(structure) == 1:
                if initial_pointers.ref_resolution_mode == RefResolutionMode.RESOLVE_REFERENCES:
                    doc_ref = DocReference(structure[initial_pointers.dollar_ref_token], root_pointers)
                    return doc_ref.resolve()
                else:
                    base_class = DocReference
                    structure = structure[initial_pointers.dollar_ref_token]
            elif initial_pointers.ref_resolution_mode == RefResolutionMode.RESOLVE_WHEN_REQUIRED:
                pass
            else:
                raise Exception(f"Ref resolution mode cannot handle structure with '{initial_pointers.dollar_ref_token}' and other properties")
    else:
        raise Exception(f"Does not support structures that are a {type(structure)}")

    class DocumentRoot(base_class, Document):

        def __init__(self, structure, pointers: IncompletePointers):
            super().__init__(structure, pointers)

    doc_root = DocumentRoot(structure, root_pointers)
    if controller.options.ref_resolution_mode == RefResolutionMode.RESOLVE_REFERENCES and hasattr(doc_root, "resolve_references"):
        doc_root.resolve_references()

    return doc_root

