# Fragwise — Claude Agent Guide

Fragwise is an open-source fragrance discovery platform with an AI chatbot guide for both beginners and connoisseurs. This file orients Anthropic-family agents (Claude Code, Claude.ai) to the project's conventions.

> Keep this file in sync with `AGENTS.md` (the broader-ecosystem mirror). If you edit one, edit both.

## Stack Summary

- Web: Next.js 15 + Tailwind + shadcn/ui (`apps/web`)
- API: FastAPI + LangGraph in Python (`apps/api`)
- Ontology: shared notes/accords taxonomy (`packages/ontology`)
- Data: Neon Postgres + pgvector, Upstash Redis, Cloudflare R2
- Auth: Clerk. LLM: OpenAI. Hosting: Vercel + Fly.io (pay-as-you-go, scale-to-zero).

## Monorepo Layout

```
apps/web/              # Next.js frontend
apps/api/              # FastAPI backend
packages/ontology/     # Shared taxonomy package
data/seed/             # Seed datasets
data/scripts/          # Ingestion + maintenance scripts
openspec/              # SDD specs and changes
```

## Workflow: Spec-Driven Development (SDD)

This project uses the SDD pipeline from `~/.claude/rules/sdd-orchestration.md`. **Do not edit production files directly for non-trivial work** — drive every change through:

1. `sdd-explore` — investigate
2. `sdd-propose` — write proposal
3. `sdd-spec` — write delta specs (Given/When/Then, RFC 2119)
4. `sdd-design` — technical design + ADRs
5. `sdd-tasks` — implementation checklist
6. `sdd-apply` — implement
7. `sdd-verify` — validate against specs
8. `sdd-archive` — sync deltas to main specs

Skill registry: see `.atl/skill-registry.md` for project-specific compact rules and skill loadout. Always consult this file when picking skills.

## Conventions

| Area | Tool | Notes |
|------|------|-------|
| Python lint | `ruff` | Configured in phase-0b |
| Python types | `mypy` | Strict mode in `apps/api` |
| TS lint | `eslint` | Next.js preset + repo overrides |
| TS types | `tsc --noEmit` | Run in CI |
| Library docs | Context7 MCP | Use `resolve-library-id` then `query-docs` before writing code that touches a third-party library |
| Commits | Minimal, no co-authored trailers | Per user preference |

## Do Not

- Do **not** bypass SDD for non-trivial changes (>~50 LOC or multiple files).
- Do **not** commit `.env` or any real secret. `.env.example` is the contract.
- Do **not** add dependencies without an `sdd-propose` step justifying the addition.
- Do **not** symlink `CLAUDE.md` and `AGENTS.md` — keep them as separate files.
- Do **not** modify the `LICENSE` file. Apache-2.0 verbatim only.
