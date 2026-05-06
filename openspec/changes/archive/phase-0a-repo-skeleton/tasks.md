# Tasks: Phase 0a — Repo Skeleton

## Phase 1: Pre-flight

- [x] 1.1 Confirm working dir is `fragwise/` repo root, branch is clean, none of the target files in `design.md §File Changes` already exist (abort if any conflict).

## Phase 2: Root Files

- [x] 2.1 Create `LICENSE` per `design.md §1 LICENSE` — fetch verbatim Apache-2.0 text from `https://www.apache.org/licenses/LICENSE-2.0.txt`. No edits.
- [x] 2.2 Create `README.md` per `design.md §2 README.md` — must include `Stack`, `Status` (mentions "Phase 0a"), `Setup` (placeholder), and `License` (Apache-2.0) sections.
- [x] 2.3 Create `.gitignore` per `design.md §3 .gitignore` — Python, Node, build, env, OS, IDE patterns.
- [x] 2.4 Create `.env.example` per `design.md §4 .env.example` — all 10 keys with placeholders + adjacent comments; no real-secret-shaped values.
- [x] 2.5 Create `CLAUDE.md` per `design.md §5 CLAUDE.md` — references `.atl/skill-registry.md`, `sdd-orchestration.md`, full SDD pipeline, "keep in sync" note.
- [x] 2.6 Create `AGENTS.md` per `design.md §6 AGENTS.md` — mirror of CLAUDE.md, ecosystem framing, mirror note present.
- [x] 2.7 Create `CONTRIBUTING.md` per `design.md §7 CONTRIBUTING.md` — references `openspec/changes/` and "Apache-2.0".
- [x] 2.8 Create `SECURITY.md` per `design.md §8 SECURITY.md` — reporting channel + 90-day disclosure.

## Phase 3: Workspace Declarations

- [x] 3.1 Create root `package.json` per `design.md §9 package.json` — `private: true`, `license: "Apache-2.0"`, `workspaces: ["apps/*","packages/*"]`, `packageManager: "pnpm@10.33.3"`, no deps.
- [x] 3.2 Create `pnpm-workspace.yaml` per `design.md §10 pnpm-workspace.yaml` — globs `apps/*`, `packages/*`.

## Phase 4: Directory Skeleton

- [x] 4.1 Create `apps/web/.gitkeep` (zero-byte) per `design.md §11`.
- [x] 4.2 Create `apps/api/.gitkeep` (zero-byte) per `design.md §11`.
- [x] 4.3 Create `packages/ontology/.gitkeep` (zero-byte) per `design.md §11`.
- [x] 4.4 Create `data/seed/.gitkeep` (zero-byte) per `design.md §11`.
- [x] 4.5 Create `data/scripts/.gitkeep` (zero-byte) per `design.md §11`.

## Phase 5: OpenSpec Config Update

- [x] 5.1 Edit `openspec/config.yaml` `context:` block per `design.md §12` — remove "License: TBD" line; append `License: Apache-2.0.` and the `pay-as-you-go, scale-to-zero` Fly.io hosting line. Leave `schema`, `rules`, etc. untouched.

## Phase 6: Self-Check

- [x] 6.1 `git add -A && git status` — confirm all 16 new files staged, working tree otherwise clean.
- [x] 6.2 Run forbidden-pattern scan per spec criterion #10: `git ls-files '*.ts' '*.tsx' '*.py' '*.sql' Dockerfile docker-compose.yml justfile Makefile '.github/workflows/*.yml'` returns empty.
- [x] 6.3 Quick grep sanity: `LICENSE` matches Apache headline; `package.json` parses as JSON with required fields; `.env.example` contains all 10 required keys; hand off to `sdd-verify`.
