from abc import ABC, abstractmethod
from typing import IO


class FetcherBaseClass(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def fetch(self, uri) -> str:
        pass


class FilesystemFetcher(FetcherBaseClass):

    def __init__(self):
        super().__init__()
        self._documents: dict[str, IO] = {}

    def add_file_io(self, uri: str, source: IO):
        self._documents[uri] = source

    def fetch(self, uri: str) -> str:
        if uri in self._documents:
            return self._documents[uri].read()
        return open(uri).read()


class PrepopulatedFetcher(FetcherBaseClass):

    def __init__(self):
        super().__init__()
        self._documents = {}

    def prepopulate(self, uri, source):
        self._documents[uri] = source

    def fetch(self, uri: str) -> str:
        return self._documents[uri]
