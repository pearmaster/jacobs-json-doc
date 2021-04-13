from abc import ABC, abstractmethod

class LoaderBaseClass(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def load(self, uri) -> str:
        pass


class FilesystemLoader(LoaderBaseClass):

    def __init__(self):
        super().__init__()

    def load(self, uri: str) -> str:
        return open(uri).read()


class PrepopulatedLoader(LoaderBaseClass):

    def __init__(self):
        super().__init__()
        self._documents = {}

    def prepopulate(self, uri, source):
        self._documents[uri] = source

    def load(self, uri: str) -> str:
        return self._documents[uri]