"""Article model: external links + topics about a fragrance."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fragwise_api.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .fragrance import Fragrance


class Article(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "articles"

    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    topics: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    fragrances: Mapped[list[Fragrance]] = relationship(
        secondary="fragrance_articles",
        back_populates="articles",
        lazy="raise_on_sql",
    )

    __table_args__ = (Index("ix_articles_slug", "slug", unique=True),)
