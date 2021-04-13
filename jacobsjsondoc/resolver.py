from abc import ABC, abstractmethod
import os.path

class ResolverBaseClass(ABC):
    
    @abstractmethod
    def resolve(self, src_uri, dest_uri):
        pass


class FilesystemResolver(ResolverBaseClass):

    def __init__(self):
        super().__init__()
    
    def resolve(self, base_uri: str, dest_uri: str) -> str:
        base = os.path.dirname(base_uri)
        return os.path.realpath(os.path.join(base, dest_uri))

class PassThroughResolver(ResolverBaseClass):

    def __init__(self):
        super().__init__()
    
    def resolve(self, base_uri: str, dest_uri: str) -> str:
        return dest_uri