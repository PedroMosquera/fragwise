"""Pydantic v2 ontology loader.

Reads ``packages/ontology/{notes.yaml, accords.yaml, synonyms.json}`` and
validates each document's shape (incl. mandatory ``version: 1``). The
loader is idempotent and side-effect free — DB writes happen in
``data/scripts/ingest_ontology.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# Path walk: ontology/ -> fragwise_api/ -> src/ -> api/ -> apps/ -> <repo root>
# parents[5] is the repo root (parents[4] is apps/, which would be wrong).
ONTOLOGY_DIR = Path(__file__).resolve().parents[5] / "packages" / "ontology"


class _BaseDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = Field(..., description="schema version")


class NoteRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    name: str
    parent_slug: str | None = None


class NotesDocument(_BaseDoc):
    notes: list[NoteRecord]


class AccordRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    name: str


class AccordsDocument(_BaseDoc):
    accords: list[AccordRecord]


class SynonymRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical: str
    synonyms: list[str]


class SynonymsDocument(_BaseDoc):
    synonyms: list[SynonymRecord]


def _read_yaml(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"ontology file not found: {path}")
    return yaml.safe_load(path.read_text())


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"ontology file not found: {path}")
    return json.loads(path.read_text())


def _validate(model: type[BaseModel], raw: Any, path: Path) -> BaseModel:
    if not isinstance(raw, dict) or "version" not in raw:
        raise ValueError(f"missing top-level 'version' field in {path}")
    try:
        return model.model_validate(raw)
    except ValidationError as e:
        raise ValueError(f"invalid ontology document at {path}: {e}") from e


def load_notes(directory: Path | None = None) -> list[NoteRecord]:
    p = (directory or ONTOLOGY_DIR) / "notes.yaml"
    doc = _validate(NotesDocument, _read_yaml(p), p)
    assert isinstance(doc, NotesDocument)
    return doc.notes


def load_accords(directory: Path | None = None) -> list[AccordRecord]:
    p = (directory or ONTOLOGY_DIR) / "accords.yaml"
    doc = _validate(AccordsDocument, _read_yaml(p), p)
    assert isinstance(doc, AccordsDocument)
    return doc.accords


def load_synonyms(directory: Path | None = None) -> list[SynonymRecord]:
    p = (directory or ONTOLOGY_DIR) / "synonyms.json"
    doc = _validate(SynonymsDocument, _read_json(p), p)
    assert isinstance(doc, SynonymsDocument)
    return doc.synonyms


__all__ = [
    "ONTOLOGY_DIR",
    "AccordRecord",
    "AccordsDocument",
    "NoteRecord",
    "NotesDocument",
    "SynonymRecord",
    "SynonymsDocument",
    "load_accords",
    "load_notes",
    "load_synonyms",
]
