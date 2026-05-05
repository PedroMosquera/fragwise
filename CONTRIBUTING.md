# Contributing to Fragwise

Thanks for considering a contribution. Fragwise is open-source under [Apache-2.0](./LICENSE), and the project follows a strict spec-driven development workflow.

## How to Propose a Change

All non-trivial changes flow through the SDD pipeline rooted at `openspec/changes/`. The lifecycle:

1. **Explore** — investigate the idea (`openspec/changes/{name}/exploration.md`).
2. **Propose** — write `proposal.md`: intent, scope, approach, rollback.
3. **Spec** — add delta specs under `openspec/changes/{name}/specs/{domain}/spec.md` using Given/When/Then with RFC 2119 keywords.
4. **Design** — `design.md` with ADRs and concrete file changes.
5. **Tasks** — `tasks.md` checklist.
6. **Apply** — implement, ticking tasks as they land.
7. **Verify** — `verify-report.md` validates each spec scenario.
8. **Archive** — merge deltas into `openspec/specs/` and move the change to `openspec/changes/archive/YYYY-MM-DD-{name}/`.

If you are using Claude Code or another agent, the `sdd-*` skills automate each step. Otherwise, follow the same artifact layout manually.

## How to Run Locally

Local development tooling (Docker Compose, justfile, lint configs) is delivered in **phase 0b**. Until that change lands, the repo is intentionally not runnable.

## Code Style

Tooling specifics (`ruff`, `mypy`, `eslint`, `prettier`, `tsc`) are pinned in **phase 0b**. Once they land, every PR must pass lint, type, and test gates.

## Licensing (Inbound = Outbound)

By submitting a contribution you agree your code is licensed under [Apache-2.0](./LICENSE), the same license as the project. No CLA is required.

## Pull Request Process

1. Open the PR against `main`.
2. Reference the `openspec/changes/{name}/` directory in the PR description.
3. Make sure `sdd-verify` passes (or a manual checklist substitute, pre-0b).
4. Squash-merge once a maintainer approves.
