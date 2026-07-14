from .document import create_document
from .fetcher import PrepopulatedFetcher
from .options import ParseOptions
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("jacobs-json-doc")
except PackageNotFoundError:
    __version__ = "unknown"


def parse(text_data):
    ppl = PrepopulatedFetcher()
    ppl.prepopulate(None, text_data)
    doc = create_document(uri=None, fetcher=ppl)
    return doc


__all__ = ["ParseOptions", "PrepopulatedFetcher"]
