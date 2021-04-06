import unittest

from loader import PrepopulatedLoader
from document import Document

class TestDocument(unittest.TestCase):

    def test_create(self):
        y = """
        jacob:
            brunson:
                - 1
                - 2
                - true
                - isa:
                    nice guy
            food:
                true
        """
    
        ppl = PrepopulatedLoader(y)
        doc = Document(uri=None, resolver=None, loader=ppl)
        print(doc)

if __name__ == '__main__':
    unittest.main()