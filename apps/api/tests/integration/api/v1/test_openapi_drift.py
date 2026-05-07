"""OpenAPI drift gate: committed file == live emission. Also F3 mapper check."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_openapi_committed_matches_live() -> None:
    from fragwise_api.main import app

    target = Path(__file__).resolve().parents[4] / "openapi.json"
    expected = (
        json.dumps(app.openapi(), sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    )
    actual = target.read_bytes()
    assert expected == actual, "apps/api/openapi.json is stale; run `just emit-openapi`"


def test_configure_mappers_no_warning() -> None:
    """F3: SQLAlchemy mappers configure cleanly with no SAWarning."""
    from sqlalchemy.exc import SAWarning

    from fragwise_api.db.base import Base

    with warnings.catch_warnings():
        warnings.simplefilter("error", SAWarning)
        Base.registry.configure()
