"""
Example: load a YAML file with jacobsjsondoc and display its contents.

example.yaml uses a `$ref` to pull the "author" section in from author.yaml,
demonstrating cross-file reference resolution. RESOLVE_REFERENCES mode is
used so `$ref`s are automatically resolved and replaced in the document tree.

Run with:
    uv run python examples/load_yaml.py
"""

import os

from jacobsjsondoc.document import create_document
from jacobsjsondoc.options import ParseOptions, RefResolutionMode


def main() -> None:
    yaml_path = os.path.join(os.path.dirname(__file__), "example.yaml")
    options = ParseOptions()
    options.ref_resolution_mode = RefResolutionMode.RESOLVE_REFERENCES
    doc = create_document(uri=yaml_path, options=options)

    print(f"Loaded document from: {yaml_path}\n")

    print(f"title: {doc['title']}")
    print(f"description: {doc['description']}")

    # `author` is defined via a $ref to author.yaml. With RESOLVE_REFERENCES
    # mode, the reference is already resolved in place, so it can be used
    # directly without calling .resolve().
    author = doc["author"]
    print("\nauthor:")
    print(f"  name: {author['name']}")
    print(f"  email: {author['email']}")

    print("\ntags:")
    for tag in doc["tags"]:
        print(f"  - {tag}")

    print("\ndetails:")
    print(
        f"  version: {doc['details']['version']} (line {doc['details']['version'].line})"
    )
    print(f"  active: {doc['details']['active']}")


if __name__ == "__main__":
    main()
