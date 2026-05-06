"""DB session smoke: SELECT 1 via make_engine + make_sessionmaker."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from fragwise_api.db.session import make_engine, make_sessionmaker

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_select_one(database_url: str) -> None:
    engine = make_engine(database_url)
    sm = make_sessionmaker(engine)
    try:
        async with sm() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
    finally:
        await engine.dispose()
