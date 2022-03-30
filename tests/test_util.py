import unittest

from jacobsjsondoc.util import merge_dicts, DictionaryMergeError

class TestDictionaryMerge(unittest.TestCase):

    def test_no_dup_merge(self):
        a = {
            1: 100,
            2: 200,
            3: {"another": "object"},
        }
        b = {
            4: 400,
            "five": ["a", "list"]
        }
        merge_dicts(a, b)
        self.assertDictEqual(a, {
            1: 100,
            2: 200,
            3: {"another": "object"},
            4: 400,
            "five": ["a", "list"]
        })

    def test_merge_dicts(self):
        a = {
            "properties": {1:100, 2:200},
            "something": "else",
        }
        b = {
            "properties": {3: 300},
            "key": True,
        }
        merge_dicts(a, b)
        self.assertDictEqual(a, {
            "properties": {1:100, 2:200, 3:300},
            "something": "else",
            "key": True,
        })
    
    def test_merge_lists(self):
        a = {
            "the_list": [1,2,3],
        }
        b = {
            "the_list": [4],
        }
        merge_dicts(a, b)
        self.assertDictEqual(a, {
            "the_list": [1,2,3,4]
        })
    
    def test_bad_merge(self):
        a = {
            "key": True
        }
        b = {
            "key": 200
        }
        with self.assertRaises(DictionaryMergeError):
            merge_dicts(a, b)