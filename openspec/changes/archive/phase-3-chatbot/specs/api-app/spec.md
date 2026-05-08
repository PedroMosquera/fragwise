# Delta for api-app

## ADDED Requirements

### Requirement: Chat Endpoint

`POST /api/v1/chat` MUST accept a JSON body `{messages: ChatMessage[], session_id?: string}` where `ChatMessage = {role: "user" | "assistant" | "system", content: string}` and respond with `Content-Type: text/event-stream` plus the header `X-Accel-Buffering: no` (to disable proxy buffering for self-hosters fronted by Nginx-class proxies). The handler MUST validate, before opening the SSE stream, that:

- `messages` is non-empty
- The last message's `role` is `"user"`
- Each `messages[i].content` is at most 4000 characters (cheap pre-check before the token-cap check)
- The `messages` array contains at most 20 entries (10 user + 10 assistant turns)

Validation failures MUST return HTTP 422 with the canonical envelope `{"error": {"code": "<code>", "message": "...", "detail": {...}}}` and MUST NOT open the SSE stream. On success, the response MUST stream events per the `agent` capability's SSE event schema and MUST terminate with a `done` event.

#### Scenario: Happy path opens SSE and terminates with done

- GIVEN a valid request body with `messages = [{role: "user", content: "smoky leather for winter"}]`
- WHEN the client POSTs `/api/v1/chat`
- THEN the response status is 200
- AND `Content-Type: text/event-stream` and `X-Accel-Buffering: no` headers are present
- AND the stream terminates with `event: done` carrying `finish_reason: "complete"`

#### Scenario: Empty messages array returns 422

- WHEN the client POSTs `{"messages": []}`
- THEN the response status is 422
- AND the body is `{"error": {"code": "invalid_request", ...}}`
- AND no SSE stream is opened

#### Scenario: Last message must be from the user

- WHEN the client POSTs `{"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]}`
- THEN the response status is 422
- AND the body's `error.code` is `"invalid_request"`
- AND no SSE stream is opened

#### Scenario: Per-message content length cap

- WHEN any `messages[i].content` exceeds 4000 characters
- THEN the response status is 422
- AND the body's `error.code` is `"invalid_request"` with detail naming the offending index

### Requirement: Chat Rate Limiting

The chat endpoint MUST enforce per-IP slowapi rate limits backed by the existing P2 Redis singleton: `5 requests / 1 hour` AND `20 requests / 1 day`, evaluated concurrently as separate windows. Limits MUST be configurable via env `FRAGWISE_CHAT_RATE_PER_IP_HOUR` (default 5) and `FRAGWISE_CHAT_RATE_PER_IP_DAY` (default 20). When EITHER threshold is exceeded the handler MUST return HTTP 429 with body `{"error": {"code": "rate_limited", "message": "..."}}` and MUST NOT open the SSE stream.

#### Scenario: 5th hourly request OK, 6th returns 429

- GIVEN an IP has issued 4 chat requests in the last hour
- WHEN it issues request 5 (valid) then 6
- THEN request 5 returns 200 with an SSE stream
- AND request 6 returns 429 with `error.code = "rate_limited"`
- AND request 6 never opens an SSE stream

#### Scenario: Daily window also enforced

- GIVEN an IP has issued 20 chat requests in the last 24 hours
- WHEN it issues request 21
- THEN the response status is 429
- AND `error.code = "rate_limited"`

#### Scenario: Window resets

- GIVEN an IP has been 429'd
- WHEN both windows have rolled past their earliest counted requests
- THEN a valid request returns 200

### Requirement: Chat Daily Kill-Switch

A global daily counter at Redis key `chat:dailycount:YYYY-MM-DD` (UTC) MUST be incremented on each chat call (including ones that ultimately error inside the stream). When the counter exceeds `FRAGWISE_DAILY_CHAT_LIMIT` (default 200), ALL chat calls MUST return HTTP 503 with body `{"error": {"code": "daily_limit_reached", "message": "..."}}` and MUST NOT open the SSE stream until the next UTC day. The first INCR of a new day MUST set EXPIRE to (next UTC midnight) + 60s buffer to ensure clean rollover. 503 MUST be reserved exclusively for the daily kill-switch; OpenAI outages MUST NOT produce 503.

#### Scenario: 201st call returns 503

- GIVEN `FRAGWISE_DAILY_CHAT_LIMIT=200` and the day's counter is at 200
- WHEN any IP issues a chat request
- THEN the response status is 503 with `error.code = "daily_limit_reached"`
- AND no SSE stream is opened

#### Scenario: Counter rolls at UTC midnight

- GIVEN the daily counter has tripped on day D
- WHEN the UTC clock crosses midnight into day D+1
- THEN a fresh `chat:dailycount:<D+1>` key starts at 0
- AND chat requests succeed again

#### Scenario: First INCR of the day sets EXPIRE

- GIVEN today's `chat:dailycount:YYYY-MM-DD` does not yet exist in Redis
- WHEN the first chat request of the day is processed
- THEN the key is INCR'd to 1
- AND TTL is set to `(seconds until next UTC midnight) + 60`

### Requirement: Chat Conversation Length Cap

The chat handler MUST enforce a hard cap of 20 messages per request (10 user-assistant turn pairs), configurable via `FRAGWISE_CHAT_MAX_TURNS` (default 10 turns = 20 messages). The check MUST run BEFORE the SSE stream is opened. Overflow MUST return HTTP 422 with body `{"error": {"code": "conversation_too_long", "message": "...", "detail": {"max_messages": 20}}}`.

#### Scenario: 20 messages OK, 21 returns 422

- GIVEN a request with `messages` length 20 (valid)
- WHEN the client POSTs the request
- THEN the response status is 200 with an SSE stream
- WHEN the client POSTs a request with `messages` length 21
- THEN the response status is 422
- AND `error.code = "conversation_too_long"` with `detail.max_messages = 20`
- AND no SSE stream is opened

### Requirement: Chat Message Token Cap

Each `ChatMessage.content` MUST be tokenized via `tiktoken` for the `gpt-4o-mini` encoder. If any message's token count exceeds 1000 (configurable via `FRAGWISE_CHAT_MAX_USER_TOKENS`, default 1000), the request MUST be REJECTED (not truncated) with HTTP 422 and body `{"error": {"code": "message_too_long", "message": "...", "detail": {"max_tokens": 1000}}}`. The check MUST run before the SSE stream is opened.

#### Scenario: 1000-token message OK, 1001 returns 422

- GIVEN a `ChatMessage.content` whose tiktoken count for `gpt-4o-mini` is exactly 1000
- WHEN the client POSTs the request
- THEN the response status is 200
- WHEN the same request is reissued with content totaling 1001 tokens
- THEN the response status is 422
- AND `error.code = "message_too_long"` with `detail.max_tokens = 1000`
- AND no SSE stream is opened
- AND the message is NOT silently truncated

### Requirement: Chat Degraded-Mode Fallback

OpenAI failures inside the agent MUST degrade per-node, NEVER 503. The handler MUST emit fallbacks as follows:

- **Intake/clarify/rank failure**: emit a `degraded` SSE event naming the failing node (`reason: "openai_intake_failed"` / `"openai_clarify_failed"` / `"openai_rank_failed"`), then fall through to a generic clarify question (intake/clarify path) or to top-1 candidate without rank-reordering (rank path), then `done` with `finish_reason: "degraded"`.
- **Retrieve embedding failure**: the retrieve node's wrapper MUST fall through to FTS-only retrieval (mirrors P2 search degraded-mode); if the wrapper falls through, emit a `degraded` event with `reason: "openai_embedding_failed"` and continue the graph normally; the final `done` MUST report `finish_reason: "complete"` (the request still produced grounded picks).
- **Explain failure**: emit a `degraded` event with `reason: "openai_explain_failed"` naming the top-1 candidate (no reasoning), then `done` with `finish_reason: "degraded"`.

503 MUST be reserved exclusively for the daily kill-switch (see `Chat Daily Kill-Switch`). OpenAI outages MUST NEVER produce 503.

#### Scenario: Intake failure degrades to generic clarify

- GIVEN OpenAI fails for the intake node after retries
- WHEN a chat request runs
- THEN a `degraded` event with `reason: "openai_intake_failed"` is emitted
- AND a generic `clarify` event follows
- AND `done` reports `finish_reason: "degraded"`
- AND the response status is 200 (NOT 503)

#### Scenario: Retrieve embedding failure falls through to FTS

- GIVEN OpenAI embedding fails after retries but the chat-completion path is healthy
- WHEN a chat request runs
- THEN a `degraded` event with `reason: "openai_embedding_failed"` is emitted
- AND retrieve uses FTS + ontology only
- AND rank and explain still run normally
- AND `done` reports `finish_reason: "complete"`

#### Scenario: Explain failure degrades to top-1 without reasoning

- GIVEN OpenAI fails specifically for the explain node after retries
- WHEN a chat request runs
- THEN a `degraded` event with `reason: "openai_explain_failed"` is emitted naming the top-1 candidate
- AND no `recommendation` events follow
- AND `done` reports `finish_reason: "degraded"`
- AND the response status is 200 (NOT 503)

#### Scenario: 503 is reserved for daily kill-switch

- GIVEN OpenAI is unreachable for every retry on every node
- AND the daily kill-switch has NOT tripped
- WHEN a chat request runs
- THEN the response status is 200 with degraded events
- AND the response status is NEVER 503 due to OpenAI outage
