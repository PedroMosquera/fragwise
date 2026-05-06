"""Perfumer model."""

from __future__ import annotations

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from fragwise_api.db.base import Base, TimestampMixin, UUIDMixin


class Perfumer(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "perfumers"

    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (Index("ix_perfumers_slug", "slug", unique=True),)
