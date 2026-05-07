"""Shared FastAPI dependencies for /api/v1.

`get_session` reads `app.state.db_sessionmaker`, which is the single source of
truth for the engine (constructed in `lifespan`). No module-level engine.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fragwise_api.db.session import get_session

DbSession = Annotated[AsyncSession, Depends(get_session)]
