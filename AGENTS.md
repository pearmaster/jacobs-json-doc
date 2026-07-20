# jacobs-json-doc

A JSON/YAML loader for Python that wraps [ruamel.yaml](https://sourceforge.net/projects/ruamel-yaml/) to provide line number tracking and `$ref` resolution (JSON Pointer references used by JSON Schema, OpenAPI, AsyncAPI, etc.).

## Project Structure

```
jacobsjsondoc/
  __init__.py        — Package entry point; exports `create_document`, `parse`, `ParseOptions`, `PrepopulatedFetcher`
  document.py        — Core document model: `create_document()`, `DocObject`, `DocArray`, `DocValue`, `DocReference`, `DocElement`, `ParseController`
  fetcher.py         — Abstract `FetcherBaseClass` with `FilesystemFetcher` and `PrepopulatedFetcher` implementations
  options.py         — `ParseOptions` and `RefResolutionMode` enum; `JsonSchemaParseOptions` subclass
  parser.py          — `Parser` class wrapping ruamel.yaml's round-trip loader
  reference.py       — `JsonPointer` class for URI parsing, fragment resolution, and reference equality
  util.py            — `merge_dicts` helper for reference property merging
tests/
  test_document.py   — Tests for document loading, types, references, circular dependencies
  test_reference.py  — Tests for JsonPointer and complex $ref resolution scenarios
  test_parse.py      — Tests for raw parsing
  test_quick_parse.py — Tests for quick parse convenience
  test_types.py      — Tests for parsed type handling
  test_util.py       — Tests for merge_dicts
  test_imports.py    — Tests for package imports
  context.py         — Test helper for import path setup
```

## Key Concepts

### Document Model

`create_document(uri, fetcher, options)` is the main entry point. It returns a document tree rooted at a `DocElement` subclass:

- **`DocObject`** (dict subclass) — JSON/YAML objects
- **`DocArray`** (list subclass) — JSON/YAML arrays
- **`DocValue`** / **`DocInteger`** / **`DocFloat`** / **`DocString`** — Scalar values with line tracking
- **`DocReference`** — A `$ref` that can be resolved via `.resolve()`

Every `DocElement` has `.line` (line number in source), `.elem_index` (key/index in parent), and `.base_uri` (current resolution scope).

### Fetchers

A `FetcherBaseClass` subclass provides the `fetch(uri) -> str` method to retrieve JSON/YAML source text. Built-in implementations:
- `FilesystemFetcher` — reads from the local filesystem
- `PrepopulatedFetcher` — in-memory, used in tests

### Reference Resolution Modes

Controlled via `ParseOptions.ref_resolution_mode`:
- `USE_REFERENCES_OBJECTS` — An object containing a `$ref` entry becomes a `DocReference` objects, and any other properties in the object are discarded.  For example `{"$ref": "#/$defs/foo", "type": "integer"}` becomes a `DocReference` that points to whatever is at `#/$defs/foo`. (default). 
- `RESOLVE_REFERENCES` — An object containg a `$ref` entry becomes the schema that is defined at the reference.  For example `{"$defs": {"foo": {"minimum": 0}}, "bar": {"$ref": "#/$defs/foo", "type": "integer"}}` becomes `{"$defs": {"foo": {"minimum": 0}}, "bar": {"minimum": 0}}`
- `RESOLVE_MERGE_PROPERTIES` — The `$ref` property of an object is replaced by the schema that is defined at the reference, merging with the siblings to the `$ref` property.  For example `{"$defs": {"foo": {"minimum": 0}}, "bar": {"$ref": "#/$defs/foo", "type": "integer"}}` becomes `{"$defs": {"foo": {"minimum": 0}}, "bar": {"minimum": 0, "type": "integer"}}`

### JsonPointer

`JsonPointer` handles URI parsing and fragment navigation. It supports relative URI resolution via `.to()` and is used throughout the document model to track resolution scope (`base_uri`).

## Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency management
- [Task](https://taskfile.dev/) for running tasks

### Commands

```sh
task check          # Run format, lint, typecheck, and tests
task test           # Run tests with pytest
task lint           # Lint with ruff
task lint-fix       # Lint and auto-fix
task format         # Format with black
task typecheck      # Type-check with mypy
task build          # Build sdist and wheel with uv
```

## Code Conventions

- Python 3.12+ required
- Full type annotations required; codebase must pass `mypy` cleanly
- Formatted with Black (`-t py314`)
- Linted with Ruff
- MIT licensed
- Tests use `unittest.TestCase` with `PrepopulatedFetcher` for in-memory test data

## Project Managment

This project uses Astral's UV.  Rather than running `python` or `pip` directly, run `uv run` or `uv pip` or `uv add`.