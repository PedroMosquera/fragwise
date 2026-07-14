# Fragwise

Fragwise is an open-source fragrance discovery platform with a built-in AI chatbot guide. It serves connoisseurs cataloging notes, accords, and houses, and beginners who just want to find a scent they will love. Project URL (once deployed): https://fragwise.app

## Status

**In active development, runnable locally, not deployed yet.** Phases 0 through 4 are complete: monorepo tooling with docker compose and a `justfile`, the Postgres + pgvector schema and fragrance ontology, catalog read endpoints, hybrid lexical + vector search, the LangGraph chat guide (Wisp), and the web UI (home, catalog and taxonomy pages, dark theme). Auth is in progress as phase 5; deployment to fragwise.app follows.

## Stack

- Web: Next.js 16 + Tailwind CSS v4 + shadcn/ui
- API: Python FastAPI + LangGraph
- Database: Neon Postgres + pgvector
- Cache / rate limit: Upstash Redis
- Object storage: Cloudflare R2
- Auth: Clerk
- LLM: OpenAI
- Hosting: Vercel (web) + Fly.io (api), pay-as-you-go with scale-to-zero
- Self-hostable via `docker-compose`

## Setup

Requires `just`, pnpm, uv (Python 3.12), and Docker.

```sh
cp .env.example .env   # fill in what you need
just install           # pnpm workspace + Python venv via uv
just db-up             # Postgres with pgvector via docker compose
just dev               # web on :3000, api on :8000
```

Run `just` with no arguments to list the full recipe set (tests, lint, migrations, db shells).

## License

Licensed under [Apache-2.0](./LICENSE). Inbound contributions are licensed outbound under the same terms; see [CONTRIBUTING.md](./CONTRIBUTING.md).
