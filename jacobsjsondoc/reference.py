
from urllib.parse import urlparse, ParseResult as UrlParseResult

class JsonReference:

    def __init__(self, scheme, netloc, path, fragment):
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.fragment = fragment
    
    @property
    def uri(self):
        return "{}://{}{}".format(self.scheme, self.netloc, self.path)
    
    @classmethod
    def from_url_parsed_result(cls, result:UrlParseResult):
        return cls(result["scheme"], result["netloc"], result["path"], result["fragment"])

    @classmethod
    def from_string(cls, input:str):
        result = urlparse(input)
        return cls.from_url_parsed_result(result)

    def copy(self):
        return RefLocation(self.scheme, self.netloc, self.path, self.fragment)

    def append_to_fragment(self, part):
        self.fragment = "{}/{}".format(self.fragment, part)
        return self

    def change_to(self, result:UrlParseResult):
        if result["scheme"] and result["netloc"]:
            self.scheme = result["scheme"]
            self.netloc = result["netloc"]
        if result["path"]:
            self.path = result["path"]
        if result["fragment"]:
            self.fragment = result["fragment"]
        return self
    
    def __eq__(self, other):
        return (self.uri == other.uri) and (self.fragment == other.fragment)
