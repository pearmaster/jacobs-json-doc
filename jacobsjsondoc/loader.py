from abc import ABC, abstractmethod

class LoaderBaseClass(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def Load(self, uri) -> str:
        pass


class FilesystemLoader(LoaderBaseClass):

    def __init__(self):
        super().__init__()

    def Load(self, uri: str) -> str:
        return open(uri).read()


class PrepopulatedLoader(LoaderBaseClass):

    def __init__(self, text):
        super().__init__()
        self._text = text

    def Load(self, uri: str) -> str:
        return self._text