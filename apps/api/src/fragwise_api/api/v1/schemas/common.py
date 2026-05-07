"""Cross-resource pydantic schemas: pagination, list envelope, error body."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Pagination(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    limit: int
    offset: int
    total: int
    has_next: bool


class ListEnvelope(BaseModel, Generic[T]):  # noqa: UP046  # pydantic v2 needs Generic[T] subclass form
    model_config = ConfigDict(from_attributes=True)
    data: list[T]
    pagination: Pagination


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: object | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody
