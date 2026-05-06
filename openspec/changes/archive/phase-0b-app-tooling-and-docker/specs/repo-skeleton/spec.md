# Delta for repo-skeleton

Phase 0b makes the workspace executable. Two requirements from the original 0a `repo-skeleton` spec must change: the "no application code or build tooling" invariant (which 0b violates by design) and the OpenSpec config-context invariant (which carried Next.js 15 / unspecified Tailwind wording from 0a).

## MODIFIED Requirements

### Requirement: Application Code And Build Tooling Allowed Under Defined Paths

The repository MAY contain application source files and build/dev tooling under explicitly permitted paths only. Permitted locations:

- `apps/web/**` — TypeScript/TSX source, Next.js config, PostCSS config, ESLint flat config, Prettier config, vitest config, Playwright config, `package.json`.
- `apps/api/**` — Python source, `pyproject.toml`, `uv.lock`, `Dockerfile`, ruff/mypy/pytest config.
- Repo root — `docker-compose.yml`, `justfile`.
- `.github/workflows/**` — GitHub Actions workflow YAML files.

Outside these paths, the original 0a constraints still hold (no stray `*.ts`, `*.tsx`, `*.py`, `*.sql`, `Dockerfile`, `Makefile`, or workflow files).

(Previously: the repo MUST NOT contain any `*.ts`, `*.tsx`, `*.py`, `*.sql`, `Dockerfile`, `docker-compose.yml`, `justfile`, `Makefile`, or `.github/workflows/*.yml` files. 0a forbade them outright; 0b relaxes the rule to permit them under the listed paths only.)

#### Scenario: Permitted application and tooling files exist under defined paths

- GIVEN a fresh clone after 0b lands
- WHEN running `git ls-files`
- THEN files matching `apps/web/**/*.{ts,tsx}`, `apps/api/**/*.py`, `apps/api/Dockerfile`, repo-root `docker-compose.yml`, repo-root `justfile`, and `.github/workflows/*.yml` MAY be present
- AND no `*.ts`, `*.tsx`, `*.py`, `*.sql`, `Dockerfile`, or workflow file exists outside those permitted paths

#### Scenario: Stray application file outside permitted paths is forbidden

- GIVEN a fresh clone
- WHEN searching for `*.ts`, `*.tsx`, or `*.py` files outside `apps/**` and `data/**` (where 0c will land scripts)
- THEN no such files are tracked
- AND searching for a `Makefile` at the repo root returns nothing

### Requirement: OpenSpec Config Reflects Locked Decisions

`openspec/config.yaml` `context:` block MUST state license as Apache-2.0, MUST clarify hosting as "pay-as-you-go Fly.io, scale-to-zero" (replacing the prior TBD/free-tier wording), AND MUST describe the web stack as "Next.js 16 + Tailwind v4 + shadcn" and the API agent layer as "LangGraph 1.x". The redundant `Hosting:` line carried over from 0a SHOULD be collapsed so the hosting clause appears exactly once.

(Previously: required Apache-2.0 + pay-as-you-go/scale-to-zero phrasing. 0b additionally requires the Next.js 16 + Tailwind v4 + shadcn descriptor, the LangGraph 1.x note, and removal of the duplicated hosting line.)

#### Scenario: Config context updated for 0b stack

- GIVEN `openspec/config.yaml`
- WHEN reading the `context:` block
- THEN it contains "Apache-2.0"
- AND it contains "pay-as-you-go" and "scale-to-zero" (or equivalent phrasing) exactly once
- AND it contains the string "Next.js 16 + Tailwind v4 + shadcn"
- AND it contains the string "LangGraph 1.x"
- AND it no longer says license is TBD
