from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError

class Parser(object):

    def __init__(self):
        self._yaml = YAML(typ='rt')

    def parse_yaml(self, data: str):
        try:
            structure = self._yaml.load(data)
        except ScannerError as e:
            fixed_data = data.replace("\t", "    ")
            structure = self._yaml.load(fixed_data)
        return structure

    def parse_json(self, data: str):
        return self.parse_yaml(data)