"""Accord model (chypre, fougere, oriental, gourmand, aquatic, woody)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fragwise_api.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .fragrance import Fragrance


class Accord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "accords"

    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    fragrances: Mapped[list[Fragrance]] = relationship(
        secondary="fragrance_accords",
        back_populates="accords",
        lazy="raise_on_sql",
    )

    __table_args__ = (Index("ix_accords_slug", "slug", unique=True),)
