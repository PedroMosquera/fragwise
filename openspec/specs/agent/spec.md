# agent Specification

## Purpose

Defines the LangGraph 1.x recommendation agent at `apps/api/src/fragwise_api/agent/`: a hand-routed `StateGraph(State)` with five nodes (intake, clarify, retrieve, rank, explain), the typed conversation state, the tiered model invariant (`gpt-4o-mini` for intake/clarify/rank; `gpt-4o` for explain), the Server-Sent Events (SSE) event schema consumed by the chat endpoint, the grounding invariant that prevents hallucinated picks, prompt-injection hardening, cancellation safety on client disconnect, and the no-checkpointer round-trip session model.

## Requirements

### Requirement: Graph Composition

`apps/api/src/fragwise_api/agent/graph.py` MUST expose a module-level compiled `StateGraph(State)` accessible via the package as `compiled` (or equivalent re-export from `agent/__init__.py`). The graph MUST wire five nodes in this order: `intake → (clarify | retrieve) → rank → explain`. The `clarify` branch MUST short-circuit the turn (skip retrieve/rank/explain) and emit a clarifying question; the next user turn MUST loop back through `intake` with the new message appended to `state.messages`. The graph MUST be compiled once at import time.

#### Scenario: Compiled graph exposes the canonical edge order

- GIVEN `fragwise_api.agent` is imported
- WHEN inspecting the compiled graph's node and edge set
- THEN nodes `{intake, clarify, retrieve, rank, explain}` are present
- AND edges encode `START → intake`, `intake → clarify (conditional) | retrieve`, `retrieve → rank`, `rank → explain`, `explain → END`, `clarify → END`

#### Scenario: Clarify short-circuits the turn

- GIVEN intake has produced `preferences` missing 2+ required fields
- WHEN the graph runs for one turn
- THEN clarify is invoked AND retrieve/rank/explain are NOT invoked for this turn
- AND the next turn (with the user's reply appended) re-enters via intake

### Requirement: State Shape

`apps/api/src/fragwise_api/agent/state.py` MUST declare `State` as a `TypedDict` containing AT LEAST: `messages: Annotated[list[BaseMessage], add_messages]`, `preferences: dict | None`, `candidates: list[FragranceCandidate]`, `picks: list[Pick]`. The `messages` reducer MUST be `langgraph.graph.add_messages`. State MAY also carry `degraded: bool` and `error: str | None` for fallback signalling.

#### Scenario: State enforces the four required keys

- GIVEN the `State` TypedDict
- WHEN type-checking nodes that read/write state
- THEN every node reads/writes only the declared keys
- AND `messages` accumulates via `add_messages`, never overwrites

### Requirement: Intake Node

`agent/nodes/intake.py` MUST extract structured `preferences` (occasion, season, gender, intensity, families, budget, references) from the latest user message via `gpt-4o-mini`. The node MUST NOT call OpenAI when the latest user message content length is below a minimum threshold (default 10 characters); in that case it MUST mark `preferences` as missing required fields so clarify takes over.

#### Scenario: Intake extracts preferences from a substantive message

- GIVEN the latest user message is `"Looking for a smoky leather for winter evenings"`
- WHEN intake runs
- THEN `gpt-4o-mini` is called once
- AND `state.preferences` contains at least `{season: "winter", occasion: "evening", families: ["leather", "smoky"]}`

#### Scenario: Intake skips OpenAI for trivial input

- GIVEN the latest user message is `"hi"` (3 chars)
- WHEN intake runs
- THEN OpenAI is NOT called
- AND `state.preferences` reflects missing fields so clarify is taken on the conditional edge

### Requirement: Clarify Node

`agent/nodes/clarify.py` MUST inspect `state.preferences` and, if 2 or more of the 5 required fields (gender, occasion, season, intensity, budget) are missing, emit a `clarify` SSE event with one targeted question and SHORT-CIRCUIT the graph for the current turn. If fewer than 2 required fields are missing, the node MUST pass through to retrieve unchanged.

#### Scenario: Two missing fields triggers a clarification

- GIVEN `preferences = {families: ["leather"]}` (missing gender, occasion, season, intensity, budget)
- WHEN clarify runs
- THEN one `clarify` SSE event is emitted with a single targeted question
- AND retrieve/rank/explain are NOT invoked this turn
- AND the stream terminates with `done` event having `finish_reason: "clarify"`

#### Scenario: Sufficient profile passes through

- GIVEN `preferences` populates 4 of the 5 required fields
- WHEN clarify runs
- THEN no `clarify` event is emitted
- AND retrieve runs next

### Requirement: Retrieve Node

`agent/nodes/retrieve.py` MUST be a thin async wrapper around `fragwise_api.search.retrieval.hybrid_retrieve` invoked via direct in-process import. It MUST NOT call `POST /api/v1/search` over HTTP loopback. The wrapper MUST mirror P2's degraded-mode (catch `openai.APIError`/`APITimeoutError`/`APIConnectionError` and fall through to FTS-only retrieval). Default top-K MUST be 10. Output MUST populate `state.candidates`.

#### Scenario: In-process call populates candidates

- GIVEN `preferences` is populated and OpenAI is reachable
- WHEN retrieve runs
- THEN `hybrid_retrieve` is invoked in-process (no HTTP call)
- AND `state.candidates` contains up to 10 `FragranceCandidate` rows
- AND each candidate carries a non-empty `match_reason`

#### Scenario: OpenAI embedding outage falls through to FTS

- GIVEN OpenAI embedding fails after retries
- WHEN retrieve runs
- THEN the wrapper executes FTS + ontology only
- AND `state.candidates` is populated from FTS results
- AND `state.degraded = True`

### Requirement: Rank Node

`agent/nodes/rank.py` MUST score each candidate in `state.candidates` against `state.preferences` using `gpt-4o-mini`. Candidates whose score falls below a configurable threshold (default 0.3) MUST be dropped; the remainder MUST be reordered by descending score. The node MUST NOT add new candidates (preserves grounding).

#### Scenario: Ranking reorders and prunes

- GIVEN 10 candidates in `state.candidates`
- WHEN rank runs
- THEN `gpt-4o-mini` is invoked at most once for the batch
- AND `state.candidates` is reordered by descending model score
- AND any candidate with score < 0.3 is removed
- AND no slug appears in output that was not in input

### Requirement: Explain Node

`agent/nodes/explain.py` MUST use `gpt-4o` with `stream=True` to produce 3-5 picks, each with reasoning text and a note breakdown. As tokens stream, the node MUST emit `token` SSE events. For each finalized pick, the node MUST emit one `recommendation` SSE event. The system prompt MUST constrain output to slugs present in `state.candidates`.

#### Scenario: Explain streams tokens and emits recommendations

- GIVEN `state.candidates` has 5 ranked rows
- WHEN explain runs
- THEN `gpt-4o` is invoked with `stream=True`
- AND `token` SSE events are emitted as text chunks arrive
- AND between 3 and 5 `recommendation` events are emitted, one per pick
- AND each pick's `fragrance.slug` exists in `state.candidates`

### Requirement: Tiered Model Invariant

`agent/constants.py` MUST define `MODEL_MINI = "gpt-4o-mini"` and `MODEL_PRO = "gpt-4o"`, env-overridable via `FRAGWISE_CHAT_MODEL_MINI` and `FRAGWISE_CHAT_MODEL_PRO`. Intake, clarify, and rank nodes MUST use `MODEL_MINI` ONLY. Explain MUST use `MODEL_PRO` ONLY. No node MAY hardcode a model identifier outside these constants.

#### Scenario: Constants are the single source of model identity

- GIVEN `agent/constants.py`
- WHEN grepping `nodes/*.py` for the strings `"gpt-4o-mini"` and `"gpt-4o"`
- THEN no occurrences are found outside `constants.py`
- AND each node imports its model from `constants`

### Requirement: SSE Event Schema

The agent's stream adapter MUST emit events on the wire in the format `event: <type>\ndata: <json>\n\n`. The following event types MUST be supported with these payloads:

| Event | Payload |
|---|---|
| `token` | `{"text": "<chunk>"}` |
| `tool_call` | `{"node": "intake\|retrieve\|rank\|explain", "phase": "start\|end"}` |
| `tool_result` | `{"node": "<name>", "summary": "<short>"}` (optional, opaque to clients) |
| `recommendation` | `{"fragrance": <FragranceListItem>, "reasoning": "<string>", "rank": <int>, "match_reason": [...]}` |
| `clarify` | `{"question": "<string>"}` |
| `degraded` | `{"reason": "<string>", "fallback": "<string>"}` |
| `error` | `{"code": "rate_limited\|daily_limit\|invalid_request\|internal", "message": "<string>"}` |
| `done` | `{"finish_reason": "complete\|clarify\|degraded\|error"}` |

The `done` event MUST always be the last event emitted; the stream MUST close after it.

#### Scenario: Happy-path stream terminates with done(complete)

- GIVEN a successful end-to-end turn
- WHEN the SSE stream completes
- THEN events appear in order: zero or more `tool_call`, then `token`* + `recommendation`* (interleaved), then `done` with `finish_reason: "complete"`
- AND no events follow `done`

#### Scenario: Clarify-path terminates with done(clarify)

- GIVEN clarify short-circuits
- WHEN the stream completes
- THEN exactly one `clarify` event is emitted before `done` with `finish_reason: "clarify"`

### Requirement: Grounding Invariant

The SSE adapter MUST validate every `recommendation` event before emission: the pick's `fragrance.slug` MUST exist in `state.candidates` for the current turn. Picks referencing slugs absent from `state.candidates` MUST be DROPPED. If ALL picks are dropped, the adapter MUST emit a `degraded` event with `reason: "no_grounded_picks"` followed by `done` with `finish_reason: "degraded"`.

#### Scenario: Hallucinated pick is dropped

- GIVEN explain emits 4 picks where 1 references a slug absent from `state.candidates`
- WHEN the SSE adapter processes the picks
- THEN exactly 3 `recommendation` events are emitted (the hallucinated one is dropped)
- AND `done` reports `finish_reason: "complete"`

#### Scenario: All-hallucinated output degrades

- GIVEN every pick references an unknown slug
- WHEN the SSE adapter processes the picks
- THEN no `recommendation` events are emitted
- AND a `degraded` event with `reason: "no_grounded_picks"` is emitted
- AND `done` reports `finish_reason: "degraded"`

### Requirement: Cancellation Safety

When the SSE client closes the connection, the `app.astream(...)` async generator MUST be cancelled via `asyncio.CancelledError` propagated from the FastAPI `StreamingResponse`. The cancellation handler MUST abort any in-flight `AsyncOpenAI` calls (chat completions, embeddings) and discard partial state. The handler MUST NOT swallow `CancelledError`; it MUST re-raise after cleanup.

#### Scenario: Client disconnect aborts OpenAI calls

- GIVEN the client closes the SSE connection mid-`gpt-4o` stream
- WHEN the `astream` generator receives `CancelledError`
- THEN the OpenAI completion stream is closed (no further token billing)
- AND no partial state is persisted
- AND `CancelledError` propagates upward

### Requirement: Prompt-Injection Hardening

System prompts MUST be immutable constants under `apps/api/src/fragwise_api/agent/prompts/` and MUST NOT be constructed by string-interpolating user message content. User content MUST flow only through `HumanMessage` (or equivalent role-tagged carriers). Every system prompt MUST include a refusal directive instructing the model to ignore user instructions that contradict the fragrance-recommendation role. Internal node identifiers used in `tool_call`/`tool_result` events SHOULD use neutral names (e.g., `retrieve`, not `search_fragrances`) to reduce the surface for instruction-following attacks.

#### Scenario: System prompts contain no user-content interpolation

- GIVEN any node module under `agent/nodes/`
- WHEN reviewing system prompt construction
- THEN system prompts are loaded as constants from `agent/prompts/`
- AND no `f"..."` or `.format(...)` interpolates `messages[-1].content` (or any user-derived field) into a system message

#### Scenario: Refusal directive present

- GIVEN every system prompt under `agent/prompts/`
- WHEN inspecting prompt text
- THEN each prompt contains a refusal clause directing the model to ignore conflicting user instructions

### Requirement: Embedding Parity

The retrieve node MUST import `EMBEDDING_MODEL` and `EMBEDDING_DIMENSIONS` from `fragwise_api.search.constants`. The agent package MUST NOT define its own embedding constants.

#### Scenario: No duplicate embedding constants

- GIVEN the agent package
- WHEN grepping for `EMBEDDING_MODEL` or `EMBEDDING_DIMENSIONS`
- THEN no definitions exist under `agent/`
- AND `agent/nodes/retrieve.py` imports both from `fragwise_api.search.constants`

### Requirement: No Checkpointer In V1

The compiled graph MUST be produced via `graph.compile()` WITHOUT a `checkpointer` argument. Conversation state MUST be round-tripped via the request body's `messages[]` array. The `session_id` field, if accepted, MUST be opaque telemetry only and MUST NOT be used for server-side state lookup.

#### Scenario: Compile call is checkpointer-free

- GIVEN `agent/graph.py`
- WHEN inspecting the call to `.compile(...)`
- THEN no `checkpointer=` keyword is present

#### Scenario: session_id is telemetry-only

- GIVEN a chat request with `session_id="abc-123"`
- WHEN the graph runs
- THEN `session_id` does NOT drive any state-store read or write
- AND the same request without `session_id` produces the same graph behavior given identical `messages`
