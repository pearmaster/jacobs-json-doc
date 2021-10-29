
from urllib.parse import urlparse, ParseResult as UrlParseResult
from collections import UserDict

class JsonReference:

    def __init__(self, scheme, netloc, path, fragment):
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.fragment = fragment
    
    @property
    def uri(self):
        return f"{self.scheme}://{self.netloc}{self.path}"
    
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
        return f"{self.uri}#{self.fragment}"

    def copy(self):
        return self.__class__(self.scheme, self.netloc, self.path, self.fragment)

    def append_to_fragment(self, part):
        self.fragment = f"{self.fragment}/{part}"
        return self

    def change_to(self, result:UrlParseResult):
        new_ref = result
        if isinstance(result, str):
            new_ref = self.from_string(result)
        if new_ref.scheme and new_ref.netloc:
            self.scheme = new_ref.scheme
            self.netloc = new_ref.netloc
        if new_ref.path:
            self.path = new_ref.path
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
    
    def get(self, uri:str):
        ref = JsonReference.from_string(uri)
        return self[ref]

    def put(self, uri:str, node):
        self[JsonReference.from_string(uri)] = node
        return self
