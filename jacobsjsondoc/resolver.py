from abc import ABC

class ResolverBaseClass(ABC):
    
    @abstractmethod
    def GetSomething():
        pass


class FilesystemResolver(ResolverBaseClass):

    def __init__(self):
        super().__init__()

    