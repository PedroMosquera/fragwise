"""Brand model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fragwise_api.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .fragrance import Fragrance


class Brand(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "brands"

    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    fragrances: Mapped[list[Fragrance]] = relationship(back_populates="brand", lazy="raise_on_sql")

    __table_args__ = (Index("ix_brands_slug", "slug", unique=True),)
