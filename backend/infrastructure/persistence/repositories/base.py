"""
EIOS Generic Repository Base

Provides common async CRUD operations.
Subclasses implement _to_model() and _to_domain() for type-safe conversion.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.base import BaseModel

DomainT = TypeVar("DomainT")
ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepository(ABC, Generic[DomainT, ModelT]):
    def __init__(self, session: AsyncSession, model_class: type[ModelT]) -> None:
        self._session = session
        self._model_class = model_class

    @abstractmethod
    def _to_model(self, entity: DomainT) -> ModelT: ...

    @abstractmethod
    def _to_domain(self, model: ModelT) -> DomainT: ...

    async def get_by_id(self, id: str) -> Optional[DomainT]:
        result = await self._session.get(self._model_class, id)
        if result is None:
            return None
        return self._to_domain(result)

    async def save(self, entity: DomainT) -> DomainT:
        model = self._to_model(entity)
        merged = await self._session.merge(model)
        await self._session.flush()
        return self._to_domain(merged)

    async def delete(self, id: str) -> None:
        model = await self._session.get(self._model_class, id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def list_all(self) -> list[DomainT]:
        stmt = select(self._model_class)
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def _list_by_field(self, field_name: str, value: str) -> list[DomainT]:
        col = getattr(self._model_class, field_name)
        stmt = select(self._model_class).where(col == value)
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def _execute_paged(
        self,
        stmt: Any,
        page: int,
        page_size: int,
    ) -> tuple[list[DomainT], int]:
        """Execute a SELECT statement with pagination. Returns (items, total_count).

        `stmt` must be a select() with all WHERE clauses already applied.
        This method adds COUNT, OFFSET, and LIMIT automatically.
        """
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        paged_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = (await self._session.execute(paged_stmt)).scalars().all()
        return [self._to_domain(r) for r in rows], total
