[![Gitpod ready-to-code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/pearmaster/jacobs-json-doc)
[![Coverage Status](https://coveralls.io/repos/github/pearmaster/jacobs-json-doc/badge.svg?branch=master)](https://coveralls.io/github/pearmaster/jacobs-json-doc?branch=master)
[![Pearmaster](https://circleci.com/gh/pearmaster/jacobs-json-doc.svg?style=shield)](https://app.circleci.com/pipelines/github/pearmaster/jacobs-json-doc)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/pearmaster/jacobs-json-doc.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/pearmaster/jacobs-json-doc/context:python)

# jacobs-json-doc
A JSON/YAML loader for Python3.

[PyYAML](https://pyyaml.org/) or [ruamel.yaml](https://sourceforge.net/projects/ruamel-yaml/) do a good job at parsing YAML or JSON into a Python object. This package wraps ruamel.yaml to provide a little bit of extra functionality.  

### Line Numbers

If you're trying to do use parts of a JSON/YAML document, and you find that the structure of the document didn't conform to a schema or expectations, then you might want to display an error saying something like "On line 123, the value of foo was missing."  This package allows easier access to the YAML/JSON line numbers by accessing the `.line` property.

### Dollar References

JSON Schema, OpenAPI, AsyncAPI, and others have a concept of references like this: `{"$ref": "other.json#/path/to/definition"}`.

The idea here is that instead of the JSON object with the `$ref` you should be able to get a JSON structure from somewhere else.  In this example, you should find a document called `other.json` and pull out a structure at `/path/to/definition`.  

#### Loader

A **loader object** (inherits from `jacobsjsondoc.loader.LoaderBaseClass`) is able to get the JSON/YAML source.  The loader can be different if you are loading from a database, filesystem, http, etc.

#### Reference Modes

Given a loader, jacobs-json-doc can deal with dollar references.  There are two modes for how it can deal with references:

 * Use `DocReference` objects.  Anywhere in the document tree where there is a `$ref` reference, a `DocReference` object is created.  
 * Automatic resolution.  Anywhere in the document tree where there is a `$ref` reference, the reference is automatically resolved and the `$ref`s are replaced with the structures that they were referencing.
 
## Examples

The [test_document.py](./tests/test_document.py) file is a good source for examples.

A very brief example is:

```py
from jacobsjsondoc.loader import FilesystemLoader
from jacobsjsondoc.document import Document, RefResolutionMode

my_document = "/path/to/example.yaml"
loader = FilesystemLoader()
doc = Document(uri=my_document, loader=loader)
print(doc['a']['b'])
print(doc['a']['b'].line)
```

If you are loading a single bit of data, without any `$ref` references, you can do it like this:

```py
import jacobsjsondoc
text_data = '{"hello":"world"}'
doc = jacobsjsondoc.parse(text_data)
```

## License

[GPLv2](./LICENSE)

