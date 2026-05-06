# Operator scripts

Run order against a freshly migrated database:

```
just db-migrate   # alembic upgrade head
just ingest       # python data/scripts/ingest_ontology.py
just seed         # python data/scripts/seed_minimal_fragrances.py
just embed        # python data/scripts/embed_fragrances.py  (needs OPENAI_API_KEY)
```

All scripts are idempotent and safe to re-run.

## CI exclusion

These scripts are NEVER invoked from CI. CI runs only the test suite,
which uses testcontainers for DB tests and stubs the OpenAI embedder.

## OPENAI_API_KEY requirement

`embed_fragrances.py` REQUIRES the `OPENAI_API_KEY` environment variable
and exits non-zero with a clear error message if it is missing. The
other scripts do not call OpenAI and have no such requirement.
