from __future__ import annotations

from urllib.parse import urlparse
from collections import UserDict
from typing import Union

class JsonPointer:

    def __init__(self, scheme, netloc, path, fragment):
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.fragment = fragment
    
    @classmethod
    def from_uri_string(cls, uri_string:str) -> JsonPointer:
        result = urlparse(uri_string)
        return cls(result.scheme, result.netloc, result.path, result.fragment)

    @classmethod
    def empty(cls) -> JsonPointer:
        return cls('', '', '', '')

    @property
    def uri(self) -> str:
        scheme = f"{self.scheme}://" if self.scheme else ""
        netpath = f"{self.netloc}{self.path}"
        return f"{scheme}{netpath}"

    def as_string(self) -> str:
        fragment = f"#{self.fragment}" if self.fragment else ""
        return f"{self.uri}{fragment}"

    def __repr__(self):
        return self.as_string()

    def copy(self) -> JsonPointer:
        return self.__class__(self.scheme, self.netloc, self.path, self.fragment)

    def to(self, reference: Union[str, JsonPointer]):
        new_ref = reference
        if isinstance(reference, str):
            new_ref = self.from_uri_string(reference)
        if new_ref.scheme:
            self.scheme = new_ref.scheme
        if new_ref.netloc:
            self.netloc = new_ref.netloc
            self.path = ""
        if new_ref.path:
            if new_ref.path.startswith("/"):
                self.path = new_ref.path
            else:
                if self.path.endswith("/"):
                    self.path += new_ref.path
                else:
                    path_parts = self.path.split("/")[:-1]
                    path_parts.extend(new_ref.path.split("/"))
                    self.path = "/".join(path_parts)
            self.fragment = ""
        if new_ref.fragment:
            self.fragment = new_ref.fragment
        return self
    
    def __eq__(self, other:Union[JsonPointer,str]):
        alt = other
        if isinstance(other, str):
            alt = self.from_uri_string(other)
        return self.__repr__() == alt.__repr__()

    def __hash__(self):
        return self.__repr__().__hash__()
