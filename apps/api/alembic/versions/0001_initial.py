"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-06

Creates the pgvector extension, ENUMs, all 11 entity + join tables, the
B-tree / GIN-FTS / HNSW indexes, and seeds the 5 canonical concentration
rows. Hand-written: alembic autogenerate cannot detect ``Vector(...)``
columns or HNSW indexes (see ADR-0014).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GENDER_VALUES = ("masc", "fem", "unisex", "genderfree")
NOTE_ROLE_VALUES = ("top", "heart", "base")


def upgrade() -> None:
    # 1. Extension owned by the migration.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. ENUM types (must precede tables that reference them).
    gender = postgresql.ENUM(*GENDER_VALUES, name="fragrance_gender", create_type=False)
    note_role = postgresql.ENUM(*NOTE_ROLE_VALUES, name="fragrance_note_role", create_type=False)
    gender.create(op.get_bind(), checkfirst=True)
    note_role.create(op.get_bind(), checkfirst=True)

    # 3. Lookup tables first (FK targets).
    op.create_table(
        "concentrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_concentrations_slug", "concentrations", ["slug"], unique=True)

    op.create_table(
        "brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_brands_slug", "brands", ["slug"], unique=True)

    op.create_table(
        "perfumers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_perfumers_slug", "perfumers", ["slug"], unique=True)

    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notes.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_notes_slug", "notes", ["slug"], unique=True)
    op.create_index("ix_notes_parent_id", "notes", ["parent_id"])

    op.create_table(
        "accords",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_accords_slug", "accords", ["slug"], unique=True)

    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("url", sa.String, nullable=True),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("topics", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_articles_slug", "articles", ["slug"], unique=True)

    # 4. Fragrances (depends on brands, concentrations, gender enum).
    op.create_table(
        "fragrances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column(
            "brand_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brands.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("year_released", sa.Integer, nullable=True),
        sa.Column("year_text", sa.String, nullable=True),
        sa.Column(
            "gender",
            postgresql.ENUM(name="fragrance_gender", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "concentration_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("concentrations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_fragrances_slug", "fragrances", ["slug"], unique=True)
    op.create_index("ix_fragrances_brand_id", "fragrances", ["brand_id"])
    op.execute(
        "CREATE INDEX ix_fragrances_fts ON fragrances "
        "USING GIN (to_tsvector('english', name || ' ' || coalesce(description, '')))"
    )

    # 5. M:M joins.
    op.create_table(
        "fragrance_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fragrance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fragrances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "note_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "role",
            postgresql.ENUM(name="fragrance_note_role", create_type=False),
            nullable=False,
        ),
        sa.Column("position", sa.Integer, nullable=True),
        sa.UniqueConstraint(
            "fragrance_id",
            "note_id",
            "role",
            name="uq_fragrance_notes_fid_nid_role",
        ),
    )
    op.create_index("ix_fragrance_notes_fragrance_id", "fragrance_notes", ["fragrance_id"])
    op.create_index("ix_fragrance_notes_note_id", "fragrance_notes", ["note_id"])

    op.create_table(
        "fragrance_perfumers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fragrance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fragrances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "perfumer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("perfumers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "fragrance_id",
            "perfumer_id",
            name="uq_fragrance_perfumers_fid_pid",
        ),
    )

    op.create_table(
        "fragrance_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fragrance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fragrances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "fragrance_id",
            "article_id",
            name="uq_fragrance_articles_fid_aid",
        ),
    )

    # 6. Embeddings.
    op.create_table(
        "fragrance_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fragrance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fragrances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("view", sa.String, nullable=False, server_default="combined"),
        sa.Column("embedding", Vector(512), nullable=False),
        sa.Column("model", sa.String, nullable=False),
        sa.Column("dimensions", sa.Integer, nullable=False),
        sa.Column("source_hash", sa.String, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "fragrance_id",
            "view",
            "model",
            "dimensions",
            name="uq_fragrance_embeddings_fid_view_model_dim",
        ),
    )
    op.create_index(
        "ix_fragrance_embeddings_hnsw",
        "fragrance_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # 7. Seed concentrations lookup (5 canonical rows).
    op.execute(
        "INSERT INTO concentrations (id, slug, name) VALUES "
        "(gen_random_uuid(), 'edp', 'Eau de Parfum'),"
        "(gen_random_uuid(), 'edt', 'Eau de Toilette'),"
        "(gen_random_uuid(), 'cologne', 'Eau de Cologne'),"
        "(gen_random_uuid(), 'parfum', 'Parfum'),"
        "(gen_random_uuid(), 'extrait', 'Extrait de Parfum')"
    )


def downgrade() -> None:
    op.drop_index("ix_fragrance_embeddings_hnsw", table_name="fragrance_embeddings")
    op.drop_table("fragrance_embeddings")
    op.drop_table("fragrance_articles")
    op.drop_table("fragrance_perfumers")
    op.drop_index("ix_fragrance_notes_note_id", table_name="fragrance_notes")
    op.drop_index("ix_fragrance_notes_fragrance_id", table_name="fragrance_notes")
    op.drop_table("fragrance_notes")
    op.execute("DROP INDEX IF EXISTS ix_fragrances_fts")
    op.drop_index("ix_fragrances_brand_id", table_name="fragrances")
    op.drop_index("ix_fragrances_slug", table_name="fragrances")
    op.drop_table("fragrances")
    op.drop_index("ix_articles_slug", table_name="articles")
    op.drop_table("articles")
    op.drop_index("ix_accords_slug", table_name="accords")
    op.drop_table("accords")
    op.drop_index("ix_notes_parent_id", table_name="notes")
    op.drop_index("ix_notes_slug", table_name="notes")
    op.drop_table("notes")
    op.drop_index("ix_perfumers_slug", table_name="perfumers")
    op.drop_table("perfumers")
    op.drop_index("ix_brands_slug", table_name="brands")
    op.drop_table("brands")
    op.drop_index("ix_concentrations_slug", table_name="concentrations")
    op.drop_table("concentrations")
    op.execute("DROP TYPE IF EXISTS fragrance_note_role")
    op.execute("DROP TYPE IF EXISTS fragrance_gender")
    op.execute("DROP EXTENSION IF EXISTS vector")
