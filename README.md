[![Gitpod ready-to-code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/pearmaster/jacobs-json-doc)

# jacobs-json-doc
A JSON/YAML loader for Python3.

[PyYAML](https://pyyaml.org/) or [ruamel.yaml](https://sourceforge.net/projects/ruamel-yaml/) do a good job at parsing YAML or JSON into a Python object. This package wraps ruamel.yaml to provide a little but extra functionality.  

### Line Numbers

If you're trying to do use parts of a JSON/YAML document, and you find that the structure of the document didn't conform to a schema or expectations, then you might want to display an error saying something like "On line 123, the value of foo was missing."  This package allows easier access to the YAML/JSON line numbers by accessing the `.line` property.

### Dollar References

JSON Schema, OpenAPI, AsyncAPI, and others have a concept of references like this: `{"$ref": "other.json#/path/to/definition"}`.

The idea here is that instead of the JSON object with the `$ref` you should be able to get a JSON structure from somewhere else.  In this example, you should find a document called `other.json` and pull out a structure at `/path/to/definition`.  

#### Resolver

But where do you find `other.json`?  Is it on the filesystem, or a database, or on the web?  Part of the answer depends on the document with the reference.  For example, if the original document was at `http://example.com/schema.json` then we might need to load `http://example.com/other.json`, but the answer would be different if originally we were using a file from the local filesystem.  A **resolver object** (inherits from `jacobsjsondoc.resolver.ResolverBaseClass`) is able to make these determinations.

#### Loader

Once the resolver object determines a URI from which a JSON/YAML document can be loaded, a **loader object** (inherits from `jacobsjsondoc.loader.LoaderBaseClass`) is able to get the JSON/YAML source.  The loader can be different if you are loading from a database, filesystem, http, etc.

#### Reference Modes

Given a resolver and loader, jacobs-json-doc can deal with dollar references.  There are two modes for how it can deal with references:

 * Use `DocReference` objects.  Anywhere in the document tree where there is a `$ref` reference, a `DocReference` object is created.  That object has methods to resolve and load the references on demand, when needed.
 * Automatic resolution.  Anywhere in the document tree where there is a `$ref` reference, the reference is automatically resolved and the `$ref`s are replaced with the structures that they were referencing.
 

