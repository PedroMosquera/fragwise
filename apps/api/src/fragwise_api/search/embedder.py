"""Query-time embedding with tenacity retry on transient OpenAI failures.

ADR-0029: on exhaustion of retries, the caller catches the exception and
falls back to FTS-only with `degraded=true`. We deliberately do NOT swallow
`asyncio.CancelledError` — client disconnects must propagate cleanly so the
OpenAI call is cancelled and we don't leak coroutines.
"""

from __future__ import annotations

import asyncio

from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .constants import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL


class EmbeddingError(RuntimeError):
    """Wraps the final exception after retries are exhausted."""


async def embed_query(text: str, client: AsyncOpenAI) -> list[float]:
    """Embed a single query string.

    Retries `APIError`/`APITimeoutError`/`APIConnectionError` up to 3 times
    with exponential backoff (1-8s). All other exceptions propagate
    immediately. On exhaustion, raises the original OpenAI exception so the
    caller can decide between degrade-and-continue or surface 500.
    """
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type((APIError, APITimeoutError, APIConnectionError)),
            reraise=True,
        ):
            with attempt:
                resp = await client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=text,
                    dimensions=EMBEDDING_DIMENSIONS,
                )
                return list(resp.data[0].embedding)
    except asyncio.CancelledError:
        # MUST propagate unwrapped — client disconnect path.
        raise
    raise EmbeddingError("embed_query: tenacity exited without yielding")
