"""Loader happy-path + error cases. No DB; marker is fine."""

from __future__ import annotations

from pathlib import Path

import pytest

from fragwise_api.ontology.loader import (
    load_accords,
    load_notes,
    load_synonyms,
)

pytestmark = pytest.mark.integration


def test_load_notes_happy_path() -> None:
    notes = load_notes()
    assert any(n.slug == "bergamot" for n in notes)
    assert any(n.slug == "citrus" and n.parent_slug is None for n in notes)


def test_load_accords_happy_path() -> None:
    accords = load_accords()
    slugs = {a.slug for a in accords}
    for required in ("chypre", "fougere", "oriental", "gourmand", "aquatic", "woody"):
        assert required in slugs


def test_load_synonyms_happy_path() -> None:
    syn = load_synonyms()
    assert any(s.canonical == "bergamot" for s in syn)


def test_loader_rejects_missing_version(tmp_path: Path) -> None:
    p = tmp_path / "notes.yaml"
    p.write_text("notes: []\n")
    with pytest.raises(Exception, match="version"):
        load_notes(directory=tmp_path)


def test_loader_rejects_unknown_version(tmp_path: Path) -> None:
    p = tmp_path / "notes.yaml"
    p.write_text("version: 2\nnotes: []\n")
    with pytest.raises(ValueError, match="invalid ontology document"):
        load_notes(directory=tmp_path)


def test_loader_rejects_missing_version_json(tmp_path: Path) -> None:
    p = tmp_path / "synonyms.json"
    p.write_text('{"synonyms": []}')
    with pytest.raises(Exception, match="version"):
        load_synonyms(directory=tmp_path)
