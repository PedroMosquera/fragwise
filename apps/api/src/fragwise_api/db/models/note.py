"""Note model with hierarchical self-FK (parent_id)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fragwise_api.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .fragrance import Fragrance
    from .joins import FragranceNote


class Note(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notes"

    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="RESTRICT"),
        nullable=True,
    )

    parent: Mapped[Note | None] = relationship(
        "Note",
        remote_side="Note.id",
        back_populates="children",
        lazy="raise_on_sql",
    )
    children: Mapped[list[Note]] = relationship(
        "Note",
        back_populates="parent",
        lazy="raise_on_sql",
        # F7: belt-and-suspenders for any joinedload use; selectinload's
        # `recursion_depth` does not strictly require `join_depth` on current
        # SQLAlchemy patches but versions vary — keep for robustness.
        join_depth=10,
    )

    fragrance_notes: Mapped[list[FragranceNote]] = relationship(
        back_populates="note",
        viewonly=True,
        lazy="raise_on_sql",
        overlaps="fragrances",
    )
    fragrances: Mapped[list[Fragrance]] = relationship(
        secondary="fragrance_notes",
        viewonly=True,
        lazy="raise_on_sql",
        overlaps="fragrance_notes,fragrance,notes,note",
    )

    __table_args__ = (
        Index("ix_notes_slug", "slug", unique=True),
        Index("ix_notes_parent_id", "parent_id"),
    )
