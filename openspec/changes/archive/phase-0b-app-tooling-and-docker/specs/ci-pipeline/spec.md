# ci-pipeline Specification

## Purpose

Defines the GitHub Actions CI surface for Fragwise: per-area workflows (`web`, `api`) with path-filtered triggers, an OpenSpec-hygiene workflow for every PR, and a manual-trigger Playwright workflow. Caching is documented and pre-commit framework hooks are explicitly excluded.

## Requirements

### Requirement: Web Workflow With Path Filters

`.github/workflows/web.yml` MUST trigger on `pull_request` and `push` to `main` with a `paths:` filter that includes at minimum `apps/web/**`, `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, AND the workflow file path itself (`.github/workflows/web.yml`). The job MUST run, in order: checkout, pnpm setup, install with cache, lint, typecheck, test, build.

#### Scenario: Web workflow triggers correctly and runs all gates

- GIVEN a PR that modifies `apps/web/app/page.tsx`
- WHEN GitHub Actions evaluates triggers
- THEN `web.yml` is queued
- AND the job runs `lint`, `typecheck`, `test`, and `build` steps in order
- AND the job exits with success on the scaffolded code

#### Scenario: Web workflow ignores api-only changes

- GIVEN a PR that modifies only files under `apps/api/**`
- WHEN GitHub Actions evaluates triggers
- THEN `web.yml` is NOT queued

### Requirement: API Workflow With Path Filters

`.github/workflows/api.yml` MUST trigger on `pull_request` and `push` to `main` with a `paths:` filter that includes at minimum `apps/api/**` AND the workflow file path itself. The job MUST run, in order: checkout, uv setup, install, ruff, mypy, pytest.

#### Scenario: API workflow triggers correctly and runs all gates

- GIVEN a PR that modifies `apps/api/src/fragwise_api/main.py`
- WHEN GitHub Actions evaluates triggers
- THEN `api.yml` is queued
- AND the job runs `ruff`, `mypy`, and `pytest` in order
- AND the job exits with success on the scaffolded code

#### Scenario: API workflow ignores web-only changes

- GIVEN a PR that modifies only files under `apps/web/**`
- WHEN GitHub Actions evaluates triggers
- THEN `api.yml` is NOT queued

### Requirement: OpenSpec Hygiene Workflow

`.github/workflows/openspec.yml` MUST trigger on every `pull_request`. It MUST assert that any newly added directory under `openspec/changes/` (excluding directories under `openspec/changes/archive/`) contains a `proposal.md` file. A bash check is acceptable; no new dependencies are required.

#### Scenario: PR adding a change without proposal fails

- GIVEN a PR that adds `openspec/changes/some-new-change/` containing only `tasks.md`
- WHEN `openspec.yml` runs
- THEN the job fails with a non-zero exit code
- AND the failure message references the missing `proposal.md`

#### Scenario: PR adding a change with proposal passes

- GIVEN a PR that adds `openspec/changes/some-new-change/proposal.md`
- WHEN `openspec.yml` runs
- THEN the job exits 0

### Requirement: Manual-Trigger Playwright Workflow

`.github/workflows/e2e.yml` MUST exist and MUST be triggered exclusively by `workflow_dispatch`. It MUST run the Playwright smoke spec from `apps/web/e2e/`. No `pull_request` or `push` trigger is permitted on this workflow.

#### Scenario: E2E never runs on PR

- GIVEN any PR is opened or updated
- WHEN GitHub Actions evaluates triggers
- THEN `e2e.yml` is NOT queued

#### Scenario: E2E runs on manual dispatch

- GIVEN a maintainer triggers the workflow via the Actions UI
- WHEN `e2e.yml` is dispatched
- THEN Playwright installs browsers and runs `apps/web/e2e/home.spec.ts`
- AND the smoke test asserting "Fragwise" passes against a freshly built app

### Requirement: Dependency Caching Documented

The web workflow SHOULD use the pnpm cache via `actions/setup-node@v4` (`cache: 'pnpm'`). The api workflow SHOULD enable the uv cache via `astral-sh/setup-uv` with `enable-cache: true` (or an equivalent manual `actions/cache` step keyed on `uv.lock`).

#### Scenario: Cache configuration is present where used

- GIVEN `web.yml` and `api.yml`
- WHEN reading their step lists
- THEN any `setup-node` step in `web.yml` declares `cache: 'pnpm'`
- AND any `setup-uv` step in `api.yml` declares `enable-cache: true`

### Requirement: No Pre-Commit Framework Config At Repo Root

The repo MUST NOT contain a `.pre-commit-config.yaml` at the root. Local lint/format enforcement is delegated to CI in 0b; framework hooks are deferred to a later phase.

#### Scenario: Pre-commit config is absent

- GIVEN the repo root
- WHEN listing files
- THEN no file named `.pre-commit-config.yaml` exists
