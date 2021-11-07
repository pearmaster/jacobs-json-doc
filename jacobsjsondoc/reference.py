
from urllib.parse import urlparse, ParseResult as UrlParseResult
from collections import UserDict
from typing import Union
from pathlib import PurePosixPath

class JsonAnchor:

    def __init__(self, scheme, netloc, path, fragment):
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.fragment = fragment
    
    @property
    def uri(self):
        if self.scheme and self.netloc:
            return f"{self.scheme}://{self.netloc}{self.path}"
        return self.path
    
    @classmethod
    def from_url_parsed_result(cls, result:UrlParseResult):
        return cls(result.scheme, result.netloc, result.path, result.fragment)

    @classmethod
    def from_string(cls, input:str):
        result = urlparse(input)
        return cls.from_url_parsed_result(result)

    @classmethod
    def empty(cls):
        return cls('', '', '', '')

    def __repr__(self):
        fragment = f"#{self.fragment}" if self.fragment else ""
        if self.path:
            return f"{self.uri}{fragment}"
        return fragment

    def copy(self):
        return self.__class__(self.scheme, self.netloc, self.path, self.fragment)

    def append_to_fragment(self, part):
        self.fragment = f"{self.fragment}/{part}"
        return self

    def change_to(self, result:Union[UrlParseResult,str]):
        new_ref = result
        if isinstance(result, str):
            new_ref = self.from_string(result)
        if new_ref.scheme and new_ref.netloc:
            self.scheme = new_ref.scheme
            self.netloc = new_ref.netloc
        if new_ref.path:
            new_path = PurePosixPath(new_ref.path)
            old_path = PurePosixPath(self.path)
            if new_path.is_absolute():
                self.path = new_ref.path
            else:
                try:
                    self.path = str(old_path.with_name(new_path))
                except (ValueError, TypeError):
                    self.path = str(old_path.joinpath(new_path))
        if new_ref.fragment:
            self.fragment = new_ref.fragment
        return self
    
    def __eq__(self, other):
        alt = other
        if isinstance(other, str):
            alt = self.from_string(other)
        return (self.uri == alt.uri) and (self.fragment == alt.fragment)

    def __hash__(self):
        return self.__repr__().__hash__()


class ReferenceDictionary(UserDict):
    
    def get(self, dollar_id:JsonAnchor):
        return self[dollar_id]

    def put(self, dollar_id:JsonAnchor, node):
        self[dollar_id] = node
        return self
