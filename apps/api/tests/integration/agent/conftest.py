"""Integration fixtures for the chat agent.

Reuses the testcontainer Postgres from the parent integration conftest,
swaps Redis for `fakeredis.aioredis.FakeRedis`, and stubs `AsyncOpenAI` with
a deterministic per-phase script registry. The OpenAI stub responds
differently per call based on the system prompt content, so a single
fixture covers intake / clarify / rank / explain / embed in one chat turn.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fakeredis.aioredis as fakeredis_async
import httpx
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

pytestmark = pytest.mark.integration

API_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# DB / migrations
# ---------------------------------------------------------------------------


def _alembic_cfg(database_url: str) -> Config:
    os.environ["DATABASE_URL"] = database_url
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    return cfg


@pytest_asyncio.fixture(scope="module")
async def chat_migrated_db(pg_container) -> AsyncIterator[str]:  # type: ignore[no-untyped-def]
    """Boot a clean DB at head for the chat integration module."""
    url = pg_container.get_connection_url()
    os.environ["DATABASE_URL"] = url
    cfg = _alembic_cfg(url)
    await asyncio.to_thread(command.downgrade, cfg, "base")
    await asyncio.to_thread(command.upgrade, cfg, "head")
    yield url


@pytest_asyncio.fixture()
async def chat_engine(chat_migrated_db: str) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(chat_migrated_db)
    try:
        yield eng
    finally:
        await eng.dispose()


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def _embedding_for(seed: int, dims: int = 512) -> list[float]:
    """Deterministic, distinct unit vectors so cosine ordering is meaningful."""
    vec = [0.0] * dims
    vec[seed % dims] = 1.0
    return vec


@pytest_asyncio.fixture()
async def chat_seeded(
    chat_engine: AsyncEngine,
) -> AsyncIterator[dict[str, Any]]:
    """Seed a tiny catalog with embeddings keyed off the search constants."""
    from fragwise_api.search.constants import (
        EMBEDDING_DIMENSIONS,
        EMBEDDING_MODEL,
        EMBEDDING_VIEW,
    )

    async with chat_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE fragrance_accords, fragrance_articles, "
                "fragrance_perfumers, fragrance_notes, fragrance_embeddings, "
                "fragrances, articles, accords, notes, perfumers, brands "
                "RESTART IDENTITY CASCADE"
            )
        )

    sm = async_sessionmaker(chat_engine, expire_on_commit=False)

    brands = {"creed": _new_uuid(), "dior": _new_uuid()}
    accords = {"smoky": _new_uuid(), "leather": _new_uuid()}
    fragrances = {
        "aventus": _new_uuid(),
        "sauvage": _new_uuid(),
        "miss-dior": _new_uuid(),
    }

    async with sm() as session:
        for slug, bid in brands.items():
            await session.execute(
                text("INSERT INTO brands (id, slug, name) VALUES (:id, :slug, :name)"),
                {"id": bid, "slug": slug, "name": slug.title()},
            )
        for slug, aid in accords.items():
            await session.execute(
                text("INSERT INTO accords (id, slug, name) VALUES (:id, :slug, :name)"),
                {"id": aid, "slug": slug, "name": slug.title()},
            )
        conc_id = (
            await session.execute(text("SELECT id FROM concentrations WHERE slug='edp'"))
        ).scalar_one()

        frag_specs = [
            ("aventus", "Aventus", brands["creed"], "masc", 2010, "smoky leather pineapple"),
            ("sauvage", "Sauvage", brands["dior"], "masc", 2015, "smoky woody bergamot"),
            ("miss-dior", "Miss Dior", brands["dior"], "fem", 2017, "fresh floral peony"),
        ]
        sql_frag = (
            "INSERT INTO fragrances "
            "(id, slug, name, brand_id, gender, year_released, "
            "concentration_id, description) "
            "VALUES (:id, :slug, :name, :bid, :gender, :year, :cid, :desc)"
        )
        for slug, name, bid, gender, year, desc in frag_specs:
            await session.execute(
                text(sql_frag),
                {
                    "id": fragrances[slug],
                    "slug": slug,
                    "name": name,
                    "bid": bid,
                    "gender": gender,
                    "year": year,
                    "cid": conc_id,
                    "desc": desc,
                },
            )

        accord_pairs = [
            (fragrances["aventus"], accords["smoky"]),
            (fragrances["aventus"], accords["leather"]),
            (fragrances["sauvage"], accords["smoky"]),
        ]
        sql_acc = (
            "INSERT INTO fragrance_accords (id, fragrance_id, accord_id) VALUES (:id, :fid, :aid)"
        )
        for fid, aid in accord_pairs:
            await session.execute(
                text(sql_acc),
                {"id": _new_uuid(), "fid": fid, "aid": aid},
            )

        embedded = ["aventus", "sauvage", "miss-dior"]
        sql_emb = (
            "INSERT INTO fragrance_embeddings "
            "(id, fragrance_id, view, embedding, model, dimensions, source_hash) "
            "VALUES (:id, :fid, :view, CAST(:emb AS vector(512)), :model, :dims, :hash)"
        )
        for i, slug in enumerate(embedded):
            await session.execute(
                text(sql_emb),
                {
                    "id": _new_uuid(),
                    "fid": fragrances[slug],
                    "view": EMBEDDING_VIEW,
                    "emb": str(_embedding_for(i)),
                    "model": EMBEDDING_MODEL,
                    "dims": EMBEDDING_DIMENSIONS,
                    "hash": f"hash-{slug}",
                },
            )

        await session.commit()

    yield {"brands": brands, "accords": accords, "fragrances": fragrances}


# ---------------------------------------------------------------------------
# Stub OpenAI client
# ---------------------------------------------------------------------------


@dataclass
class StubScript:
    """Per-phase script for the StubAsyncOpenAI client."""

    intake_prefs: dict[str, Any] = field(
        default_factory=lambda: {
            "gender": "masculine",
            "occasion": "evening",
            "season": "winter",
            "intensity": "strong",
            "families": ["smoky", "leather"],
            "budget": "high",
        }
    )
    clarify_question: str = "What season do you wear it in?"
    rank_scores: dict[str, float] = field(
        default_factory=lambda: {"aventus": 0.95, "sauvage": 0.85, "miss-dior": 0.45}
    )
    explain_picks: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {
                "slug": "aventus",
                "rank": 1,
                "reasoning": "Bold smoky-leather signature for winter evenings.",
            },
            {
                "slug": "sauvage",
                "rank": 2,
                "reasoning": "Smoky alternative with a fresher opening.",
            },
            {
                "slug": "miss-dior",
                "rank": 3,
                "reasoning": "Lighter contrast pick if mood shifts feminine.",
            },
        ]
    )
    intake_raises: bool = False
    rank_raises: bool = False
    explain_raises: bool = False
    embed_raises: bool = False


class _ChatChoiceMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _ChatChoice:
    def __init__(self, content: str) -> None:
        self.message = _ChatChoiceMessage(content)


class _ChatCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [_ChatChoice(content)]


class _Delta:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _StreamChoice:
    def __init__(self, content: str | None) -> None:
        self.delta = _Delta(content)


class _StreamEvent:
    def __init__(self, content: str | None) -> None:
        self.choices = [_StreamChoice(content)]


class _StreamIterator:
    """Async iterator emitting one chunk per pick line. Supports `aclose()`."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self._i = 0
        self.aclose_called = False

    def __aiter__(self) -> _StreamIterator:
        return self

    async def __anext__(self) -> _StreamEvent:
        if self._i >= len(self._lines):
            raise StopAsyncIteration
        line = self._lines[self._i]
        self._i += 1
        return _StreamEvent(line)

    async def aclose(self) -> None:
        self.aclose_called = True


class _ChatCompletions:
    def __init__(self, parent: _StubChat) -> None:
        self._parent = parent

    async def create(self, **kwargs: Any) -> Any:
        script = self._parent._script
        messages = kwargs.get("messages", [])
        sys_text = ""
        for m in messages:
            if isinstance(m, dict) and m.get("role") == "system":
                sys_text = m.get("content", "")
                break
        if "intake stage" in sys_text:
            if script.intake_raises:
                from openai import APIError

                raise APIError("intake stub failure", request=None, body=None)  # type: ignore[arg-type]
            return _ChatCompletion(json.dumps(script.intake_prefs))
        if "clarify stage" in sys_text:
            return _ChatCompletion(script.clarify_question)
        if "rank stage" in sys_text:
            if script.rank_raises:
                from openai import APIError

                raise APIError("rank stub failure", request=None, body=None)  # type: ignore[arg-type]
            return _ChatCompletion(
                json.dumps(
                    {"scores": [{"slug": s, "score": v} for s, v in script.rank_scores.items()]}
                )
            )
        if "explain stage" in sys_text:
            if script.explain_raises:
                from openai import APIError

                raise APIError("explain stub failure", request=None, body=None)  # type: ignore[arg-type]
            lines = [json.dumps(p) + "\n" for p in script.explain_picks]
            return _StreamIterator(lines)
        # Default: empty content.
        return _ChatCompletion("{}")


class _StubChat:
    def __init__(self, script: StubScript) -> None:
        self._script = script
        self.completions = _ChatCompletions(self)


class _StubEmbeddings:
    def __init__(self, script: StubScript) -> None:
        self._script = script

    async def create(self, **kwargs: Any) -> Any:
        if self._script.embed_raises:
            from openai import APIError

            raise APIError("embedding stub failure", request=None, body=None)  # type: ignore[arg-type]
        item = type("E", (), {"embedding": _embedding_for(0)})()
        return type("R", (), {"data": [item]})()


class StubAsyncOpenAI:
    """Deterministic AsyncOpenAI stand-in keyed by per-node system prompt."""

    def __init__(self, script: StubScript | None = None) -> None:
        self.script = script or StubScript()
        self.chat = _StubChat(self.script)
        self.embeddings = _StubEmbeddings(self.script)
        self.streams: list[_StreamIterator] = []  # populated in tests if needed

    async def close(self) -> None:
        return None


# ---------------------------------------------------------------------------
# SSE consumer
# ---------------------------------------------------------------------------


@dataclass
class SSEEvent:
    event: str
    data: dict[str, Any]


def _parse_sse_block(block: str) -> SSEEvent | None:
    ev = ""
    payload = ""
    for line in block.splitlines():
        if line.startswith("event:"):
            ev = line[len("event:") :].strip()
        elif line.startswith("data:"):
            payload += line[len("data:") :].strip()
    if not ev:
        return None
    return SSEEvent(event=ev, data=json.loads(payload) if payload else {})


async def consume_sse(
    client: httpx.AsyncClient, body: dict[str, Any]
) -> tuple[int, list[SSEEvent], dict[str, Any] | None]:
    """POST /api/v1/chat, parse SSE stream into typed events.

    Returns `(status_code, events, error_body_or_None)`. `error_body` is the
    JSON envelope when status != 200; `events` is empty in that case.
    """
    out: list[SSEEvent] = []
    async with client.stream("POST", "/api/v1/chat", json=body) as resp:
        if resp.status_code != 200:
            payload_bytes = await resp.aread()
            try:
                err = json.loads(payload_bytes.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                err = None
            return resp.status_code, [], err
        buf = ""
        async for chunk in resp.aiter_text():
            buf += chunk
            while "\n\n" in buf:
                block, buf = buf.split("\n\n", 1)
                ev = _parse_sse_block(block)
                if ev:
                    out.append(ev)
    return 200, out, None


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


def _make_chat_app(
    engine: AsyncEngine,
    redis_client: Any,
    openai_client: Any,
) -> Any:
    """Build an app whose lifespan was bypassed; inject test doubles."""
    import tiktoken

    from fragwise_api.agent.rate_limit import chat_limiter, set_chat_storage_uri
    from fragwise_api.db.session import make_sessionmaker
    from fragwise_api.main import create_app
    from fragwise_api.search.rate_limit import limiter, set_storage_uri

    # Reset slowapi state between tests so per-IP windows start fresh.
    set_storage_uri("memory://")
    limiter.reset()
    set_chat_storage_uri("memory://")
    chat_limiter.reset()

    app = create_app()
    app.state.db_engine = engine
    app.state.db_sessionmaker = make_sessionmaker(engine)
    app.state.redis = redis_client
    app.state.openai_client = openai_client
    app.state.limiter = limiter
    app.state.chat_limiter = chat_limiter
    app.state.tiktoken_encoder = tiktoken.encoding_for_model("gpt-4o-mini")
    return app


@pytest.fixture()
def fake_redis() -> Iterator[fakeredis_async.FakeRedis]:
    r = fakeredis_async.FakeRedis(decode_responses=False)
    yield r


@pytest.fixture()
def stub_openai_script() -> StubScript:
    """Override per-test to mutate intake/rank/explain stub responses."""
    return StubScript()


@pytest.fixture()
def stub_openai(stub_openai_script: StubScript) -> StubAsyncOpenAI:
    return StubAsyncOpenAI(stub_openai_script)


@pytest_asyncio.fixture()
async def chat_client(
    chat_engine: AsyncEngine,
    chat_seeded: dict[str, Any],
    fake_redis: Any,
    stub_openai: StubAsyncOpenAI,
) -> AsyncIterator[httpx.AsyncClient]:
    app = _make_chat_app(chat_engine, fake_redis, stub_openai)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
