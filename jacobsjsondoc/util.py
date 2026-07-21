from typing import Dict


class DictionaryMergeError(Exception):
    pass


def merge_dicts(to_dict: Dict, from_dict: Dict, skip_existing: bool = False):
    for k, v in from_dict.items():
        if k in to_dict:
            if isinstance(v, dict) and isinstance(to_dict[k], dict):
                merge_dicts(to_dict[k], v, skip_existing=skip_existing)
            elif skip_existing:
                continue
            elif isinstance(v, list) and isinstance(to_dict[k], list):
                to_dict[k].extend(v)
            else:
                raise DictionaryMergeError("Key exists in both dictionaries")
        else:
            to_dict[k] = v
