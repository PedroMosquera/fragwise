# Fragwise

Fragwise is an open-source fragrance discovery platform with a built-in AI chatbot guide. It serves connoisseurs cataloging notes, accords, and houses, and beginners who just want to find a scent they will love. Project URL (once deployed): https://fragwise.app

## Status

**Phase 0a — repo skeleton only.** This repository currently contains structural and legal scaffolding. There is no runnable code yet. Application code, tooling, and the data model arrive in phases 0b and 0c.

## Stack

- Web: Next.js 15 + Tailwind CSS + shadcn/ui
- API: Python FastAPI + LangGraph
- Database: Neon Postgres + pgvector
- Cache / rate limit: Upstash Redis
- Object storage: Cloudflare R2
- Auth: Clerk
- LLM: OpenAI
- Hosting: Vercel (web) + Fly.io (api), pay-as-you-go with scale-to-zero
- Self-hostable via `docker-compose` (delivered in phase 0b)

## Setup

Local setup instructions arrive in **phase 0b** along with `docker-compose.yml`, the dev `justfile`, and lint/type configs. Until then, this repo is not runnable.

## License

Licensed under [Apache-2.0](./LICENSE). Inbound contributions are licensed outbound under the same terms; see [CONTRIBUTING.md](./CONTRIBUTING.md).
