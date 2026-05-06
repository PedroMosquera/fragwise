"""Database package: SQLAlchemy models, session, and shared helpers."""

from __future__ import annotations

import hashlib


def compute_source_hash(name: str, description: str | None, notes_csv: str) -> str:
    """SHA-256 of `name|description|notes_csv`.

    Both `seed_minimal_fragrances.py` and `embed_fragrances.py` MUST call
    this same helper so that a fragrance's idempotency key is consistent
    across seed-time storage and embed-time comparison.

    `notes_csv` is the alphabetized comma-joined slugs of all associated
    notes (e.g., ``"bergamot,jasmine,oakmoss"``).
    """
    payload = f"{name}|{description or ''}|{notes_csv}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = ["compute_source_hash"]
