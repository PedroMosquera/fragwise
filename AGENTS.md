# Fragwise — Agent Guide (AGENTS.md)

This is the ecosystem-standard agent guide for Fragwise, mirroring `CLAUDE.md`. Tools that read `AGENTS.md` (Cursor, Aider, Codex, Continue, Cline, etc.) should treat this file as authoritative.

> Keep this file in sync with `CLAUDE.md`. If you edit one, edit both.

## Project Pitch

Fragwise is an open-source fragrance discovery platform with an AI chatbot guide. It serves both connoisseurs (notes, accords, houses) and beginners (natural-language scent discovery).

## Stack Summary

- Web: Next.js 15 + Tailwind + shadcn/ui (`apps/web`)
- API: FastAPI + LangGraph in Python (`apps/api`)
- Ontology package: `packages/ontology`
- Data: Neon Postgres + pgvector, Upstash Redis, Cloudflare R2
- Auth: Clerk. LLM: OpenAI. Hosting: Vercel + Fly.io (pay-as-you-go, scale-to-zero).

## Monorepo Layout

```
apps/web/              # Next.js frontend
apps/api/              # FastAPI backend
packages/ontology/     # Shared taxonomy
data/seed/             # Seed datasets
data/scripts/          # Ingestion + maintenance scripts
openspec/              # SDD specs and changes
```

## Workflow: Spec-Driven Development

Fragwise uses the SDD pipeline (see `~/.claude/rules/sdd-orchestration.md`). All non-trivial work flows through:

`sdd-explore` -> `sdd-propose` -> `sdd-spec` -> `sdd-design` -> `sdd-tasks` -> `sdd-apply` -> `sdd-verify` -> `sdd-archive`

Project skill registry and compact rules live at `.atl/skill-registry.md`.

## Conventions

| Area | Tool |
|------|------|
| Python lint | ruff |
| Python types | mypy |
| TypeScript lint | eslint |
| TypeScript types | tsc --noEmit |
| Library docs | Context7 MCP (resolve-library-id then query-docs) |

## Do Not

- Do not bypass SDD for non-trivial changes.
- Do not commit `.env` or real secrets — `.env.example` is the contract.
- Do not add dependencies without a proposal.
- Do not symlink this file with `CLAUDE.md`.
- Do not modify `LICENSE`.
