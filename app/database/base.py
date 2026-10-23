"""
SQLAlchemy declarative base.

All ORM models inherit from `Base` so Alembic can autogenerate migrations
by scanning the `app.modules.*.models` modules.

We also keep pgvector's `Vector` type registered here so migrations that
add VECTOR columns work.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        # CamelCase -> snake_case
        name = cls.__name__
        out = []
        for i, ch in enumerate(name):
            if ch.isupper() and i > 0:
                out.append("_")
            out.append(ch.lower())
        return "".join(out)