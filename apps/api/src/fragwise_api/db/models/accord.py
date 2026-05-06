"""Accord model (chypre, fougere, oriental, gourmand, aquatic, woody)."""

from __future__ import annotations

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from fragwise_api.db.base import Base, TimestampMixin, UUIDMixin


class Accord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "accords"

    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (Index("ix_accords_slug", "slug", unique=True),)
