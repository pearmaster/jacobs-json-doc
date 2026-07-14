from .document import create_document
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("jacobs-json-doc")
except PackageNotFoundError:
    __version__ = "unknown"

from .loader import PrepopulatedLoader


def parse(text_data):
    ppl = PrepopulatedLoader()
    ppl.prepopulate(None, text_data)
    doc = create_document(uri=None, loader=ppl)
    return doc


from .options import ParseOptions

__all__ = [ParseOptions, PrepopulatedLoader]
