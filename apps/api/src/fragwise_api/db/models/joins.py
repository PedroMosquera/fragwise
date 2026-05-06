"""M:M join tables between fragrances and notes / perfumers / articles."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from fragwise_api.db.base import Base, UUIDMixin
from fragwise_api.db.enums import NoteRole

note_role_enum = ENUM(
    NoteRole,
    name="fragrance_note_role",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)


class FragranceNote(UUIDMixin, Base):
    __tablename__ = "fragrance_notes"

    fragrance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fragrances.id", ondelete="CASCADE"),
        nullable=False,
    )
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role: Mapped[NoteRole] = mapped_column(note_role_enum, nullable=False)
    position: Mapped[int | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fragrance_id",
            "note_id",
            "role",
            name="uq_fragrance_notes_fid_nid_role",
        ),
        Index("ix_fragrance_notes_fragrance_id", "fragrance_id"),
        Index("ix_fragrance_notes_note_id", "note_id"),
    )


class FragrancePerfumer(UUIDMixin, Base):
    __tablename__ = "fragrance_perfumers"

    fragrance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fragrances.id", ondelete="CASCADE"),
        nullable=False,
    )
    perfumer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("perfumers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "fragrance_id",
            "perfumer_id",
            name="uq_fragrance_perfumers_fid_pid",
        ),
    )


class FragranceArticle(UUIDMixin, Base):
    __tablename__ = "fragrance_articles"

    fragrance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fragrances.id", ondelete="CASCADE"),
        nullable=False,
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "fragrance_id",
            "article_id",
            name="uq_fragrance_articles_fid_aid",
        ),
    )
