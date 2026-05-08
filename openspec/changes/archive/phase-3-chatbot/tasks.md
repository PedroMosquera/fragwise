# Tasks: Phase 3 — Chatbot Agent

## Apply discipline (read first)

Per orchestrator retrospective on subagent quality:

1. **Smoke-import every new module** before marking the task done. Use
   `cd apps/api && uv run python -c "from fragwise_api.agent import <module>"`
   — if it fails (circular import, missing export, syntax error), STOP and
   fix before moving on.
2. **Run `just test-api` (unit) after every batch of 3-5 tasks**. If unit
   tests fail, fix BEFORE the next task.
3. **For framework decisions, use Context7** (resolve-library-id then
   query-docs) — NOT training-data memory. Specifically verify:
   - LangGraph 1.0.8 `StateGraph` + `add_messages` reducer +
     `add_conditional_edges` API
   - `tiktoken.encoding_for_model("gpt-4o-mini")` returns `o200k_base`
   - slowapi multi-window (stacked `@limiter.limit`) decorator semantics
   - FastAPI `StreamingResponse(media_type="text/event-stream")` headers
4. **Output reporting discipline**: paste last 10 lines of:
   - `cd apps/api && uv run pytest -q -m "not integration"` (unit)
   - `cd apps/api && uv run pytest -q -m integration tests/integration/agent/`
     (integration)
   - `cd apps/api && uv run mypy src` (typecheck)
   - `cd apps/api && uv run ruff check . && uv run ruff format --check .`
     (lint)

## Phase 1: Pre-flight

- [x] 1.1 Verify branch state: P1 + P2 archived (`openspec/specs/{search,api-app}/spec.md` reflect P2 deltas), `apps/api/openapi.json` committed and clean, `apps/api/src/fragwise_api/agent.py` stub still present (deleted in 9.1). Confirm `langgraph~=1.0.8` already pinned in `apps/api/pyproject.toml`. (~5 min)

## Phase 2: Dependencies

- [x] 2.1 Add `tiktoken>=0.7,<1.0` to `apps/api/pyproject.toml` `[project].dependencies`; run `cd apps/api && uv lock && uv sync`; commit regenerated `uv.lock`. **Verify with**: `uv run python -c "import tiktoken; print(tiktoken.encoding_for_model('gpt-4o-mini').name)"` prints `o200k_base`. (~10 min)

## Phase 3: Core agent package

- [x] 3.1 Create `apps/api/src/fragwise_api/agent/__init__.py` and `apps/api/src/fragwise_api/agent/constants.py` per `design.md §"agent/constants.py"` (tiered models, budgets, caps, profile fields). **Verify**: `uv run python -c "from fragwise_api.agent.constants import MODEL_FAST, MODEL_SMART, DAILY_CAP_DEFAULT, REQUIRED_PROFILE_FIELDS"`. (~10 min)
- [x] 3.2 Create `apps/api/src/fragwise_api/agent/state.py` with `FragranceCandidate` + `Pick` frozen dataclasses and `State` TypedDict using `Annotated[list[BaseMessage], add_messages]` per `design.md §"agent/state.py"`. **Verify**: `uv run python -c "from fragwise_api.agent.state import State, FragranceCandidate, Pick"`. (~10 min)
- [x] 3.3 Create `apps/api/src/fragwise_api/agent/schemas.py` with pydantic v2 `ChatMessage` + `ChatRequest` (last-must-be-user validator, MAX_MESSAGES, MAX_CHARS_PER_MESSAGE) per `design.md §"agent/schemas.py"`. **Verify**: `uv run python -c "from fragwise_api.agent.schemas import ChatRequest, ChatMessage"`. (~10 min)
- [x] 3.4 Create `apps/api/src/fragwise_api/agent/prompts/{__init__,intake,clarify,rank,explain}.py` — four immutable system-prompt constants per `design.md §"agent/prompts/*.py"`. Each MUST contain refusal directive verbatim per agent spec Requirement: Prompt-Injection Hardening. **Verify**: grep test asserting "REFUSAL DIRECTIVE" appears in each prompt module. (~15 min)
- [x] 3.5 Create `apps/api/src/fragwise_api/agent/graph.py` with `_needs_clarification` predicate, `_build()` factory, and module-level `compiled = _build().compile()` (no `checkpointer=`). Wire `START → intake → (clarify|retrieve) → rank → explain → END` per `design.md §"agent/graph.py"`. **Verify**: `uv run python -c "from fragwise_api.agent.graph import compiled; print(sorted(compiled.get_graph().nodes))"` lists `{intake, clarify, retrieve, rank, explain}`. (~15 min)

## Phase 4: Nodes

- [x] 4.1 Create `apps/api/src/fragwise_api/agent/nodes/__init__.py` and `apps/api/src/fragwise_api/agent/nodes/intake.py` per `design.md §"agent/nodes/intake.py"` (gpt-4o-mini, JSON-mode, INTAKE_MIN_CHARS skip, refusal handling). **Verify**: smoke-import + `_last_user_text({"messages": []})` returns `""`. (~15 min)
- [x] 4.2 Create `apps/api/src/fragwise_api/agent/nodes/clarify.py` per `design.md §"agent/nodes/clarify.py"` — emits `AIMessage` with `additional_kwargs={"chat_event":"clarify"}`. **Verify**: smoke-import. (~10 min)
- [x] 4.3 Create `apps/api/src/fragwise_api/agent/nodes/retrieve.py` per `design.md §"agent/nodes/retrieve.py"` — in-process `hybrid_retrieve` wrapper, embedding via `search.embedder`, FTS fallback on `APIError`, joinedload of `Fragrance.brand`. **Verify**: smoke-import + `_query_text({"families":["leather"], "season":"winter"})` returns non-empty. (~25 min)
- [x] 4.4 Create `apps/api/src/fragwise_api/agent/nodes/rank.py` per `design.md §"agent/nodes/rank.py"` — gpt-4o-mini JSON-mode scoring, threshold-prune, never adds slugs. **Verify**: smoke-import. (~15 min)
- [x] 4.5 Create `apps/api/src/fragwise_api/agent/nodes/explain.py` per `design.md §"agent/nodes/explain.py"` — gpt-4o `stream=True`, accumulates chunks, emits `AIMessage` with `chat_event="explain"` + `candidate_slugs` allow-list. **Verify**: smoke-import + `from fragwise_api.agent.graph import compiled` still succeeds. (~20 min)

## Phase 5: SSE adapter + grounding

- [x] 5.1 Create `apps/api/src/fragwise_api/agent/sse.py` per `design.md §"agent/sse.py"` — `_sse(event,data)` byte-encoder, `_validate_pick(line, allowed)` grounding validator (drops slugs not in allow-list), `stream_chat_response(graph, inputs, config, candidate_lookup)` with `try/except CancelledError: raise` and `finally: yield done`. All-hallucinated path emits `degraded(no_grounded_picks)`. **Verify**: smoke-import + unit-call `_validate_pick('{"slug":"x"}', set())` returns `None`. (~30 min)

## Phase 6: Cost controls

- [x] 6.1 Create `apps/api/src/fragwise_api/agent/rate_limit.py` with module-level `chat_limiter = make_chat_limiter(...)` mirroring `search/rate_limit.py` singleton pattern + `set_chat_storage_uri(redis_url)` rebind hook + env-driven `per_ip_hour()` / `per_ip_day()` rate-string helpers per `design.md §"agent/rate_limit.py"` and recommendation note (path "a"). **Verify**: smoke-import + `per_ip_hour() == "5/hour"` with default env. (~20 min)
- [x] 6.2 Create `apps/api/src/fragwise_api/agent/daily_limit.py` per `design.md §"agent/daily_limit.py"` — `chat:dailycount:YYYY-MM-DD` INCR + EXPIRE on first hit, raises `ChatDailyLimitReached` over cap. Mirrors P2 `search/daily_limit.py`. **Verify**: smoke-import + unit test of `_day_key` and `_seconds_until_next_utc_midnight`. (~15 min)

## Phase 7: Router + lifespan

- [x] 7.1 Create `apps/api/src/fragwise_api/agent/router.py` per `design.md §"agent/router.py"` — `POST /api/v1/chat`, tiktoken token-cap loop (raises 422 `message_too_long`), daily INCR (raises 503 `daily_limit_reached`), stacked `@chat_limiter.limit(per_ip_hour)` + `@chat_limiter.limit(per_ip_day)` decorators (path "a" from design note), `StreamingResponse(media_type="text/event-stream", headers={"X-Accel-Buffering":"no","Cache-Control":"no-cache"})`. Uses `_to_lc_messages(req)` to convert. **Verify**: smoke-import; OpenAPI generation does not raise. (~30 min)
- [x] 7.2 Modify `apps/api/src/fragwise_api/main.py` lifespan per `design.md §"main.py Lifespan Additions"` — add `tiktoken.encoding_for_model("gpt-4o-mini")` to `app.state.tiktoken_encoder` (ADR-0038), call `set_chat_storage_uri(redis_url)`, set `app.state.chat_limiter = chat_limiter`, `app.include_router(chat_router)`. **Verify**: `cd apps/api && uv run python -c "from fragwise_api.main import create_app; app = create_app(); print([r.path for r in app.routes if 'chat' in r.path])"`. (~15 min)

## Phase 8: OpenAPI re-emit

- [x] 8.1 Run `just emit-openapi` (or equivalent recipe). Verify `apps/api/openapi.json` now contains the `/api/v1/chat` POST path with `text/event-stream` permissive schema (ADR-0037). Commit. **Verify**: `jq '.paths."/api/v1/chat".post' apps/api/openapi.json` returns non-null; drift gate passes. (~10 min)

## Phase 9: Stub agent.py removal

- [x] 9.1 Delete `apps/api/src/fragwise_api/agent.py` (P0c stub). Run `cd apps/api && uv run grep -r "from fragwise_api.agent import" src/ tests/` and confirm ALL imports now resolve to the new package (not the stub). **Verify**: `cd apps/api && uv run python -c "import fragwise_api.agent; print(fragwise_api.agent.__file__)"` ends in `agent/__init__.py`. (~5 min)

## Phase 10: Justfile

- [x] 10.1 Add `chat-shell MSG="smoky leather for winter"` recipe to root `justfile` per `design.md §"Justfile Recipe"` (curl `-N` flag, never CI). **Verify**: `just --list | grep chat-shell`. (~5 min)

## Phase 11: Integration tests

- [x] 11.1 Create `apps/api/tests/integration/agent/__init__.py` + `conftest.py` per `design.md §"tests/integration/agent/conftest.py"` — reuses shared `postgres_url` fixture, `fakeredis.aioredis.FakeRedis`, `StubAsyncOpenAI` keyed by phase (`intake|clarify|rank|explain|embed`) with deterministic per-node responses + chat-completion async-iter for explain stream, `app_with_stubs` fixture, `consume_sse(client, body) -> list[SSEEvent]` helper. **Verify**: `cd apps/api && uv run pytest -q --collect-only tests/integration/agent/ 2>&1 | tail -5`. (~45 min)
- [x] 11.2 Write `tests/integration/agent/test_chat_happy.py` (asserts 200 + SSE order ends `done(complete)` per agent spec scenario "Happy-path stream terminates with done(complete)") and `test_chat_clarify.py` (sparse prefs → exactly one `clarify` event then `done(clarify)`). (~30 min)
- [x] 11.3 Write `tests/integration/agent/test_chat_grounding.py` covering both agent-spec scenarios: (a) "Hallucinated pick is dropped" — explain emits 4 picks, 1 unknown slug → 3 `recommendation` events + `done(complete)`; (b) "All-hallucinated output degrades" — all unknown → 0 `recommendation`, `degraded(no_grounded_picks)` + `done(degraded)`. **F-equivalent verification of grounding invariant.** (~30 min)
- [x] 11.4 Write `tests/integration/agent/test_chat_cancellation.py` (client closes mid-explain stream → stub asserts `aclose` called, `CancelledError` propagates) and `test_chat_overflow.py` (1001-token msg → 422 `message_too_long`; 21 messages → 422 `conversation_too_long`; empty → 422 `invalid_request`; last role=assistant → 422). (~30 min)
- [x] 11.5 Write `tests/integration/agent/test_chat_rate_limit.py` (6th request in 1h → 429 envelope, no SSE), `test_chat_daily_kill_switch.py` (preset `chat:dailycount:<today>=200` → 503 envelope per api-app spec), `test_chat_degraded.py` covering all three api-app spec scenarios: intake-failure → `degraded(openai_intake_failed)` + 200; embedding-failure → `degraded(openai_embedding_failed)` + `done(complete)`; explain-failure → `degraded(openai_explain_failed)` + `done(degraded)`; assert NEVER 503 from OpenAI outage. (~45 min)

## Phase 12: Self-check

- [x] 12.1 `cd apps/api && uv sync` clean; run `just lint-api` (ruff check + ruff format --check + mypy strict on src) and `just test-api` (unit, `-m "not integration"`); paste last 10 lines of each. Fix any failures. (~15 min)
- [x] 12.2 Run `just test-integration` (or `cd apps/api && uv run pytest -q -m integration tests/integration/agent/`) if Docker available; paste last 10 lines. Confirm all 8 integration suites pass with stubbed `AsyncOpenAI`. Confirm grounding test (11.3) explicitly asserts dropped picks (F-equivalent verification per orchestrator brief). (~15 min)
- [x] 12.3 Manual smoke: `just chat-shell "smoky leather for winter"` against locally running API (`OPENAI_API_KEY` set) prints a valid SSE stream ending in `event: done`. Confirm OpenAPI drift gate green (`apps/api/openapi.json` matches re-emit). Tick all `proposal.md §Success Criteria` boxes. (~10 min)
