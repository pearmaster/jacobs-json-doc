from ruamel.yaml import YAML

class Parser(object):

    def __init__(self):
        self._yaml = YAML(typ='rt')

    def Parse(self, data: str):
        structure = self._yaml(data)
        return structure
