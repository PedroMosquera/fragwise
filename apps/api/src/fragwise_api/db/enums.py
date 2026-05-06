"""Python enums backing the PG ENUM types declared in the initial migration."""

from __future__ import annotations

import enum


class Gender(enum.StrEnum):
    """Maps to PG ENUM ``fragrance_gender``."""

    masc = "masc"
    fem = "fem"
    unisex = "unisex"
    genderfree = "genderfree"


class NoteRole(enum.StrEnum):
    """Maps to PG ENUM ``fragrance_note_role``."""

    top = "top"
    heart = "heart"
    base = "base"
