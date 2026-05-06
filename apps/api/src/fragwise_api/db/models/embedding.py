"""FragranceEmbedding model: pgvector(512) + provenance fields."""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from fragwise_api.db.base import Base, UUIDMixin


class FragranceEmbedding(UUIDMixin, Base):
    __tablename__ = "fragrance_embeddings"

    fragrance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fragrances.id", ondelete="CASCADE"),
        nullable=False,
    )
    view: Mapped[str] = mapped_column(String, nullable=False, server_default="combined")
    embedding: Mapped[list[float]] = mapped_column(Vector(512), nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    dimensions: Mapped[int] = mapped_column(nullable=False)
    source_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "fragrance_id",
            "view",
            "model",
            "dimensions",
            name="uq_fragrance_embeddings_fid_view_model_dim",
        ),
    )
