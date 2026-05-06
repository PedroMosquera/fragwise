"""Concentration lookup model (edp, edt, cologne, parfum, extrait)."""

from __future__ import annotations

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from fragwise_api.db.base import Base, TimestampMixin, UUIDMixin


class Concentration(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "concentrations"

    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (Index("ix_concentrations_slug", "slug", unique=True),)
