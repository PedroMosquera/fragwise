"""Declarative base, UUID v7 generator, and common timestamp mixins."""

from __future__ import annotations

import uuid
from datetime import datetime

import uuid_utils
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid7() -> uuid.UUID:
    """Stdlib-compatible UUID v7. Cast Rust object to native ``uuid.UUID``."""
    return uuid.UUID(str(uuid_utils.uuid7()))


class Base(AsyncAttrs, DeclarativeBase):
    """Declarative base for all ORM models."""


class UUIDMixin:
    """Adds a UUID v7 primary key column named ``id``."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid7,
    )


class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` TIMESTAMPTZ columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
