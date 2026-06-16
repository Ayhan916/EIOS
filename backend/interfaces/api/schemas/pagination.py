from __future__ import annotations

import math
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, computed_field

T = TypeVar("T")


class PaginationParams:
    """FastAPI dependency for page/page_size query parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @computed_field  # type: ignore[misc]
    @property
    def total_pages(self) -> int:
        return max(1, math.ceil(self.total / self.page_size)) if self.page_size else 1

    @computed_field  # type: ignore[misc]
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @computed_field  # type: ignore[misc]
    @property
    def has_prev(self) -> bool:
        return self.page > 1
