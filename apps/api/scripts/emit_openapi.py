"""Emit a deterministic apps/api/openapi.json from app.openapi()."""

from __future__ import annotations

import json
from pathlib import Path

from fragwise_api.main import app


def emit() -> None:
    schema = app.openapi()
    encoded = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    target = Path(__file__).resolve().parents[1] / "openapi.json"
    target.write_bytes(encoded)


if __name__ == "__main__":
    emit()
