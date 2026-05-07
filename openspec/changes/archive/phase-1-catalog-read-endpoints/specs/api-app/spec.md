# Delta for api-app

## ADDED Requirements

### Requirement: Catalog API Available Under /api/v1/

The 12 catalog read routes (defined in the `catalog-api` capability) MUST be mounted under the `/api/v1/` prefix via per-resource `APIRouter` instances. The existing `/healthz` and `/readyz` endpoints MUST remain at the repository root and MUST NOT be re-mounted under `/api/v1/`.

#### Scenario: Versioned routes mounted, health probes unversioned

- GIVEN the FastAPI app is running
- WHEN sending `GET /api/v1/fragrances`, `GET /api/v1/brands`, `GET /api/v1/perfumers`, `GET /api/v1/notes`, `GET /api/v1/accords`, `GET /api/v1/articles`
- THEN every request returns status 200 with a list-envelope body
- AND `GET /healthz` returns 200 with `{"status": "ok"}`
- AND `GET /readyz` returns 200 with `{"status": "ready"}`
- AND `GET /api/v1/healthz` returns 404

### Requirement: Static OpenAPI Emission

The repository MUST commit `apps/api/openapi.json`. An emit script (e.g. `apps/api/scripts/emit_openapi.py`) MUST exist that imports `fragwise_api.main:app`, calls `app.openapi()`, and writes the result to `apps/api/openapi.json` using deterministic JSON serialization (sorted keys, `(",", ":")` separators, UTF-8 with trailing newline). A `just emit-openapi` recipe MUST run the script. The CI workflow `.github/workflows/api.yml` MUST include a step that runs the emit script and fails if `git diff --exit-code apps/api/openapi.json` reports any changes.

The committed bytes of `apps/api/openapi.json` MUST equal the deterministic serialization of the live `app.openapi()` output.

#### Scenario: Emit script produces a deterministic file

- GIVEN the api project is installed
- WHEN running `cd apps/api && uv run python scripts/emit_openapi.py`
- THEN the script writes `apps/api/openapi.json` with sorted-keys deterministic JSON
- AND running the script a second time produces a byte-identical file (no diff)

#### Scenario: CI drift gate fails on stale file

- GIVEN `apps/api/openapi.json` is out of date relative to the live schema
- WHEN the `.github/workflows/api.yml` OpenAPI emission step runs
- THEN the step exits non-zero
- AND the workflow log indicates `apps/api/openapi.json` is stale and must be regenerated

#### Scenario: Live schema is byte-equal to the committed file

- GIVEN the committed `apps/api/openapi.json`
- WHEN computing `json.dumps(app.openapi(), sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"`
- THEN those bytes equal the bytes of the committed file
