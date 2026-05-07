"""fragrance_accords join

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fragrance_accords",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fragrance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fragrances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "accord_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accords.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("fragrance_id", "accord_id", name="uq_fragrance_accords_fid_aid"),
    )
    op.create_index("ix_fragrance_accords_fragrance_id", "fragrance_accords", ["fragrance_id"])
    op.create_index("ix_fragrance_accords_accord_id", "fragrance_accords", ["accord_id"])


def downgrade() -> None:
    op.drop_index("ix_fragrance_accords_accord_id", table_name="fragrance_accords")
    op.drop_index("ix_fragrance_accords_fragrance_id", table_name="fragrance_accords")
    op.drop_table("fragrance_accords")
