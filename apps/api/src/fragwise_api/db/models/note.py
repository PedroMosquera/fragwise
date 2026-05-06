"""Note model with hierarchical self-FK (parent_id)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from fragwise_api.db.base import Base, TimestampMixin, UUIDMixin


class Note(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notes"

    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="RESTRICT"),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_notes_slug", "slug", unique=True),
        Index("ix_notes_parent_id", "parent_id"),
    )
