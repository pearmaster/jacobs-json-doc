from abc import ABC

class LoaderBaseClass(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def Load(self, uri) -> dict:
        pass


class FilesystemLoader(LoaderBaseClass):

    def __init__(self):
        super().__init__()

    def Load(self, uri: str) -> dict:
        return open(uri).read()
