from abc import ABC, abstractmethod


class FetcherBaseClass(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def fetch(self, uri) -> str:
        pass


class FilesystemFetcher(FetcherBaseClass):

    def __init__(self):
        super().__init__()

    def fetch(self, uri: str) -> str:
        return open(uri).read()


class PrepopulatedFetcher(FetcherBaseClass):

    def __init__(self):
        super().__init__()
        self._documents = {}

    def prepopulate(self, uri, source):
        self._documents[uri] = source

    def fetch(self, uri: str) -> str:
        return self._documents[uri]
