from ruamel.yaml import YAML

class Parser(object):

    def __init__(self):
        self._yaml = YAML(typ='rt')

    def parse_yaml(self, data: str):
        structure = self._yaml.load(data)
        return structure

    def parse_json(self, data: str):
        return self.parse_yaml(data)