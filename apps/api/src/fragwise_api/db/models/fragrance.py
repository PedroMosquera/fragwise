"""Fragrance model: the central content entity."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fragwise_api.db.base import Base, TimestampMixin, UUIDMixin
from fragwise_api.db.enums import Gender

if TYPE_CHECKING:
    from .accord import Accord
    from .article import Article
    from .brand import Brand
    from .concentration import Concentration
    from .joins import FragranceNote
    from .note import Note
    from .perfumer import Perfumer

# PG ENUM created by alembic 0001_initial; do not let SQLAlchemy CREATE/DROP it.
gender_enum = ENUM(
    Gender,
    name="fragrance_gender",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)


class Fragrance(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "fragrances"

    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=False,
    )
    year_released: Mapped[int | None] = mapped_column(nullable=True)
    year_text: Mapped[str | None] = mapped_column(String, nullable=True)
    gender: Mapped[Gender] = mapped_column(gender_enum, nullable=False)
    concentration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concentrations.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    brand: Mapped[Brand] = relationship(back_populates="fragrances", lazy="raise_on_sql")
    concentration: Mapped[Concentration | None] = relationship(lazy="raise_on_sql")

    # Association object owning the cascade — carries `role` enum.
    fragrance_notes: Mapped[list[FragranceNote]] = relationship(
        back_populates="fragrance",
        lazy="raise_on_sql",
        cascade="all, delete-orphan",
        overlaps="notes",
    )
    # Plain read-only view of notes via secondary; coexists with assoc obj
    # (overlaps acknowledges shared FK cols).
    notes: Mapped[list[Note]] = relationship(
        secondary="fragrance_notes",
        viewonly=True,
        overlaps="fragrance_notes,note",
        lazy="raise_on_sql",
    )
    perfumers: Mapped[list[Perfumer]] = relationship(
        secondary="fragrance_perfumers",
        back_populates="fragrances",
        lazy="raise_on_sql",
    )
    accords: Mapped[list[Accord]] = relationship(
        secondary="fragrance_accords",
        back_populates="fragrances",
        lazy="raise_on_sql",
    )
    articles: Mapped[list[Article]] = relationship(
        secondary="fragrance_articles",
        back_populates="fragrances",
        lazy="raise_on_sql",
    )

    __table_args__ = (
        Index("ix_fragrances_brand_id", "brand_id"),
        Index("ix_fragrances_slug", "slug", unique=True),
    )
