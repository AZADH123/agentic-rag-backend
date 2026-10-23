"""
Document repository — pure DB access for the documents table.

Repositories intentionally have no business logic, no I/O beyond the DB,
and no knowledge of HTTP. They return ORM objects (or scalars).
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.models import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, document_id: str) -> Optional[Document]:
        return await self._session.get(Document, document_id)

    async def list_by_owner(
        self,
        owner_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Document], int]:
        stmt = select(Document).where(Document.owner_id == owner_id).order_by(
            Document.created_at.desc()
        )
        items = (await self._session.execute(stmt.limit(limit).offset(offset))).scalars().all()

        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(Document).where(
            Document.owner_id == owner_id
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        return items, total

    async def list_all(self, limit: int = 50, offset: int = 0) -> tuple[Sequence[Document], int]:
        stmt = select(Document).order_by(Document.created_at.desc())
        items = (await self._session.execute(stmt.limit(limit).offset(offset))).scalars().all()

        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(Document)
        total = (await self._session.execute(count_stmt)).scalar_one()
        return items, total

    async def create(self, document: Document) -> Document:
        self._session.add(document)
        await self._session.flush()
        return document

    async def update_status(
        self,
        document_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        values: dict = {"status": status}
        if error is not None:
            values["error"] = error
        await self._session.execute(
            update(Document).where(Document.document_id == document_id).values(**values)
        )

    async def delete(self, document_id: str) -> None:
        doc = await self.get(document_id)
        if doc is not None:
            await self._session.delete(doc)

    async def find_by_hash(self, content_hash: str, owner_id: str) -> Optional[Document]:
        stmt = select(Document).where(
            Document.content_hash == content_hash,
            Document.owner_id == owner_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()