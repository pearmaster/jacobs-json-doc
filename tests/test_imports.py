import unittest

class TestImports(unittest.TestCase):

    def test_import_options(self):
        from jacobsjsondoc import ParseOptions
        po = ParseOptions()
        self.assertIsInstance(po, object)