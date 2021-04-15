try:
    from .document import Document
except ModuleNotFoundError:
    import sys
    if 'setup' not in sys.modules['__main__'].__file__:
        raise
from . import _version

__version__ = _version.__version__
__version_info__ = _version.__version_info__