# Proposal: Phase 0a — Repo Skeleton

## Intent

Establish the legal, contractual, and structural foundation of the Fragwise monorepo before any code lands. Closes the unknowns that block every later change: license (so external contributions are legally clean), env-var contract (so contributors know which secrets exist), agent guidance files (so AI agents share project conventions), and the directory shape (so phase 0b/0c have unambiguous places to drop files). No application code, no dependencies, no infrastructure — just the skeleton.

## Scope

### In Scope
- `LICENSE` — Apache-2.0 boilerplate
- `README.md` — project pitch + placeholders for setup steps (filled in 0b/0c)
- `.gitignore` — Python, Node, macOS, common IDEs (VSCode, JetBrains)
- `.env.example` — commented placeholders grouped by service: `OPENAI_API_KEY`, `DATABASE_URL`, `REDIS_URL` (Upstash), R2 keys (`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`), Clerk keys (`CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`), Fly.io (`FLY_API_TOKEN`)
- `CLAUDE.md` — agent guidance referencing `.atl/skill-registry.md` and the SDD workflow
- `AGENTS.md` — same content as CLAUDE.md (broader convention; keep as a copy, not a symlink, for cross-platform safety)
- `CONTRIBUTING.md` — short contribution flow + link to SDD process
- `SECURITY.md` — one-liner: report to maintainer email
- Top-level `package.json` — pnpm workspace declaration only (`workspaces: ["apps/*", "packages/*"]`, `private: true`, `packageManager` pin); NO dependencies
- Empty directories with `.gitkeep`: `apps/web/`, `apps/api/`, `packages/ontology/`, `data/seed/`, `data/scripts/`

### Out of Scope (deferred)
- Any app code, lockfiles, or installed dependencies → **phase-0b**
- `docker-compose.yml`, `justfile`, GitHub Actions workflows → **phase-0b**
- Alembic, DB schema, ontology content, pydantic validators → **phase-0c**
- `.editorconfig`, `.prettierrc`, ESLint/ruff/mypy configs → **phase-0b**

## Capabilities

### New Capabilities
None. Phase 0a is pure scaffolding — no behavioral spec applies. Specs begin in phase-0b (dev-tooling) and phase-0c (data model + ontology).

### Modified Capabilities
None.

## Approach

1. Generate root files from minimal templates; keep every file under 60 lines where possible.
2. Use `.gitkeep` to commit empty directories so phase-0b/0c can drop files into known paths without a chicken-and-egg.
3. CLAUDE.md and AGENTS.md are duplicated (not symlinked) — symlinks fragment on Windows and confuse some Git GUIs. Drift cost is low at this size.
4. The pnpm workspace declaration is added now (cheap) but no `pnpm install` is run; lockfile generation belongs to 0b.
5. License text is the verbatim Apache-2.0 boilerplate from apache.org/licenses/LICENSE-2.0.txt — no modifications.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| repo root | New | `LICENSE`, `README.md`, `.gitignore`, `.env.example`, `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`, `package.json` |
| `apps/web/` | New (empty) | `.gitkeep` only |
| `apps/api/` | New (empty) | `.gitkeep` only |
| `packages/ontology/` | New (empty) | `.gitkeep` only |
| `data/seed/`, `data/scripts/` | New (empty) | `.gitkeep` only |
| `openspec/config.yaml` | Modified | Update `context:` block — license set to Apache-2.0; hosting note clarified to "pay-as-you-go Fly.io, scale-to-zero" |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| License pick is permanent — Apache-2.0 means a closed-source SaaS clone is legally permitted | Low | User explicitly chose Apache-2.0 after seeing AGPLv3 alternative; documented in exploration U1 |
| pnpm workspace declaration commits us to pnpm; switching to npm/yarn later means lockfile churn | Low | pnpm is the recommended Vercel default for Next.js 15; reversal is mechanical (delete `pnpm-lock.yaml`, edit `package.json`) |
| CLAUDE.md / AGENTS.md drift over time since they are duplicated | Low | Add a one-line note in each file: "Keep in sync with the other; see CONTRIBUTING.md" |
| `.env.example` placeholders may become stale as services change | Low | File is reviewed in 0b/0c whenever a service is wired in |
| Free-tier resource impact | None | Phase 0a creates no runtime resources |

## Rollback Plan

`git reset --hard HEAD~N` (where N = the number of 0a commits) or `git revert` the merge commit. No production state, no migrations, no external accounts touched. Trivial.

## Dependencies

- None. Phase 0a has no external prerequisites and blocks phase-0b and phase-0c.

## Success Criteria

- [ ] `LICENSE` file exists and contains verbatim Apache-2.0 text
- [ ] `.env.example` documents every variable named in the locked stack (OpenAI, Postgres, Upstash Redis, R2, Clerk, Fly.io)
- [ ] `CLAUDE.md` and `AGENTS.md` both reference `.atl/skill-registry.md` and the SDD workflow
- [ ] Root `package.json` declares `workspaces: ["apps/*", "packages/*"]` with `private: true` and pins `packageManager`
- [ ] All five skeleton directories (`apps/web`, `apps/api`, `packages/ontology`, `data/seed`, `data/scripts`) exist and are tracked via `.gitkeep`
- [ ] `openspec/config.yaml` `context:` block updated to reflect Apache-2.0 license and pay-as-you-go Fly.io hosting
- [ ] `git status` is clean after the change merges; no untracked files left behind
