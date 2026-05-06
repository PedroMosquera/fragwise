# Ontology File Schema (v1)

All three files MUST declare a top-level `version: 1`. The loader rejects
files without `version` and files declaring an unknown version.

## notes.yaml

```yaml
version: 1
notes:
  - { slug: <kebab>, name: <display>, parent_slug: <kebab|null> }
```

Slugs MUST be unique. `parent_slug` MAY reference any other slug in the
same file. Tree depth is 1 (top-level + leaf) for v1.

## accords.yaml

```yaml
version: 1
accords:
  - { slug: <kebab>, name: <display> }
```

Slugs MUST be unique.

## synonyms.json

```json
{ "version": 1,
  "synonyms": [
    { "canonical": "<slug>", "synonyms": ["<text>", ...] }
  ] }
```

`canonical` SHOULD reference an existing note or accord slug. Search
uses synonyms to expand user queries.

## Validation

The loader validates with pydantic v2 (`extra=forbid`). Unknown fields
fail loudly. Missing `version` fails loudly. Loader is idempotent and
free of side effects — DB writes happen in `ingest_ontology.py`.
