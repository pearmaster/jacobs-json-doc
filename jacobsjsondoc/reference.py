from __future__ import annotations

from urllib.parse import urlparse
from typing import Union


class JsonPointer:

    def __init__(self, scheme: str, netloc: str, path: str, fragment: str):
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.fragment = fragment

    @classmethod
    def from_uri_string(cls, uri_string: str) -> JsonPointer:
        result = urlparse(uri_string)
        return cls(result.scheme, result.netloc, result.path, result.fragment)

    @classmethod
    def empty(cls) -> JsonPointer:
        return cls("", "", "", "")

    @property
    def uri(self) -> str:
        scheme = f"{self.scheme}://" if self.scheme else ""
        netpath = f"{self.netloc}{self.path}"
        return f"{scheme}{netpath}"

    def as_string(self) -> str:
        fragment = f"#{self.fragment}" if self.fragment else ""
        return f"{self.uri}{fragment}"

    def __repr__(self) -> str:
        return self.as_string()

    def copy(self) -> JsonPointer:
        return self.__class__(self.scheme, self.netloc, self.path, self.fragment)

    @staticmethod
    def _remove_dot_segments(path: str) -> str:
        """Normalize `.`/`..` segments in a URI path per RFC 3986 section 5.2.4."""
        if not path:
            return path
        leading_slash = path.startswith("/")
        trailing_slash = path.endswith("/")
        out: list = []
        for part in path.split("/"):
            if part == "" or part == ".":
                continue
            if part == "..":
                if out:
                    out.pop()
                continue
            out.append(part)
        normalized = "/".join(out)
        if leading_slash:
            normalized = "/" + normalized
        if trailing_slash and not normalized.endswith("/"):
            normalized += "/"
        return normalized

    def to(self, reference: Union[str, JsonPointer]) -> JsonPointer:
        new_ref: JsonPointer
        if isinstance(reference, str):
            new_ref = self.from_uri_string(reference)
        else:
            new_ref = reference
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
            self.path = self._remove_dot_segments(self.path)
            self.fragment = ""
        if new_ref.fragment:
            self.fragment = new_ref.fragment
        return self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (JsonPointer, str)):
            return NotImplemented  # type: ignore[return-value]
        alt: JsonPointer
        if isinstance(other, str):
            alt = self.from_uri_string(other)
        else:
            alt = other
        return self.__repr__() == alt.__repr__()

    def __hash__(self) -> int:
        return hash(self.__repr__())
