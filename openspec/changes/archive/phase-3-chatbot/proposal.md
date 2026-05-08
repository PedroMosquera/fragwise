# Proposal: Phase 3 — Chatbot Agent

## Intent

Land the user-facing recommendation chatbot: a streaming `POST /api/v1/chat`
endpoint backed by a hand-routed LangGraph 1.x agent (intake → clarify → retrieve
→ rank → explain). Reuses P2 infrastructure (lifespan singletons, `hybrid_retrieve`,
slowapi, Redis daily counter). Tighter cost controls than search by design (each
turn fans out to 3-5 LLM calls). See exploration §Recommendation.

## Scope

### In Scope
- `POST /api/v1/chat` SSE endpoint (events: `token`, `tool_call`, `tool_result`,
  `recommendation`, `clarify`, `degraded`, `error`, `done`) — exploration §G
- LangGraph package `apps/api/src/fragwise_api/agent/`: `state.py`, `graph.py`,
  `nodes/{intake,clarify,retrieve,rank,explain}.py`, `prompts/`, `sse.py`
- Tiered models: `gpt-4o-mini` (intake/clarify/rank), `gpt-4o` (explain)
- In-process retrieve via thin wrapper around `search.retrieval.hybrid_retrieve`
  (Q1) — exploration §A.3
- Round-trip `messages[]` per request; `session_id` opaque telemetry only (Q2,
  Q12) — exploration §D.1
- Cost controls: 5/hour + 20/day per IP (Q4); daily kill-switch 200/day at
  `chat:dailycount:YYYY-MM-DD` (Q5); 10-turn convo cap (Q6); 1000-token user
  message cap, reject (Q7) — exploration §F
- Grounding validator at SSE adapter: explain output filtered against
  `state.candidates` slugs — exploration §I
- Prompt-injection hardening: immutable system prompts, internal tool naming —
  exploration §J
- Cancellation safety: `asyncio.CancelledError` aborts OpenAI calls
- Integration tests (stubbed `AsyncOpenAI`): happy, clarify, grounding,
  cancellation, rate-limit, daily kill-switch, overflow, degraded
- `just chat-shell` recipe (manual smoke; never CI)
- OpenAPI re-emit (permissive SSE schema, drift gate)

### Out of Scope
- Tool-calling / `create_react_agent` (defer to P3b) — exploration §E
- Persistent session store, cross-session memory, checkpointer
- Web UI (P4+)
- Per-user rate limiting (no auth yet)
- Chat-level response cache (Q10) and search cache reuse
- Real OpenAI calls in CI

## Capabilities

### New Capabilities
- `agent`: graph composition, node contracts, `State` TypedDict shape, SSE event
  schema, grounding invariant, prompt-injection hardening, cancellation safety,
  tiered model selection (Q9)

### Modified Capabilities
- `api-app`: add `POST /api/v1/chat` endpoint; chat rate limit (5/h + 20/d per
  IP); chat daily kill-switch (200/d); conversation length cap (10 turns);
  message token cap (1000, reject); chat degraded-mode fallback

## Approach

Hand-routed `StateGraph(State)` with five nodes, compiled once at import. SSE
adapter wraps `app.astream(stream_mode="messages")` and validates explain
output against retrieved candidate slugs. Mirror P2 patterns for rate limit,
daily counter, and degraded-mode (FTS fallback inside retrieve wrapper). No
new infrastructure: reuse `app.state.{openai_client,redis,db_engine,limiter}`.
Vanilla `StreamingResponse` with `X-Accel-Buffering: no` (Q11). Tiktoken used
for token counting if not already pinned.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/api/src/fragwise_api/agent/` | New (replaces stub `agent.py`) | Graph, nodes, prompts, SSE adapter |
| `apps/api/src/fragwise_api/api/v1/routers/chat.py` | New | Chat router |
| `apps/api/src/fragwise_api/chat/` | New | rate_limit, daily_limit, schemas |
| `apps/api/src/fragwise_api/main.py` | Modified | Register chat router + limiter |
| `apps/api/tests/integration/agent/` | New | 8 integration suites |
| `apps/api/pyproject.toml` | Possibly modified | Confirm tiktoken pin |
| `apps/api/openapi.json` | Modified | Re-emit (drift gate) |
| `justfile` | Modified | `chat-shell` recipe |
| `openspec/specs/agent/spec.md` | New | Capability spec |
| `openspec/specs/api-app/spec.md` | Delta | 6 new requirements |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cost runaway | High | Layered: per-IP h+d, daily kill-switch, msg+convo caps, per-call max_tokens |
| Hallucination | Med | Hard grounding validator at SSE adapter; explain prompt restricts to candidate slugs |
| Prompt injection | Med | Immutable system prompts; pydantic-validated tool args; refusal directive |
| OpenAI outage | Med | Per-node fallbacks; `degraded` event; FTS fallback in retrieve; 503 only on daily cap |
| SSE proxy buffering | Low | `X-Accel-Buffering: no` header; document for self-hosters |
| Client disconnect leak | Med | `asyncio.CancelledError` handler around `astream` generator |
| Worker affinity | Low | No checkpointer in V1; flag for future `RedisSaver` migration |
| OpenAPI SSE shape | Low | Permissive schema; documented limitation |
| Embedding drift | Low | Reuse `search/constants.py` (P2 mitigation) |
| Convo-cap UX cliff | Low | Accept for V1; future "summarize-and-restart" UX |

## Rollback Plan

- Pre-merge: `git reset`.
- Post-merge pre-deploy: revert merge commit.
- Post-deploy: revert; no migrations to roll back; Redis counter + cache keys
  roll over naturally at midnight UTC.

## Dependencies

- P2 lifespan singletons (`openai_client`, `redis`, `db_engine`, `limiter`)
- P2 retrieval surface (`search.retrieval.hybrid_retrieve`,
  `search/constants.py`)
- P0c LangGraph pin (`langgraph~=1.0.8`); confirm `tiktoken` is available

## Success Criteria

- [ ] `POST /api/v1/chat` returns SSE stream with all 8 documented event types
- [ ] All 8 integration suites pass with stubbed `AsyncOpenAI`
- [ ] Grounding test: explain MUST NOT reference slugs outside `state.candidates`
- [ ] Rate-limit test: 6th request in an hour returns 429 (envelope)
- [ ] Daily kill-switch test: 201st call returns 503 (envelope)
- [ ] Overflow test: 1001-token message or 11-turn convo returns 422
- [ ] Cancellation test: client disconnect cancels OpenAI calls within 1s
- [ ] OpenAPI drift gate green after re-emit
- [ ] `just chat-shell` produces a valid SSE stream against a live local server
