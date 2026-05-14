"""
Database layer — SQLAlchemy 2.0 with typed Mapped[] columns.

Exposes:
- engine: Singleton SQLAlchemy engine
- SessionLocal: Session factory bound to the engine
- Base: Declarative base for all ORM models
- get_db: FastAPI dependency yielding a session per request
"""
from __future__ import annotations

from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models. SQLAlchemy 2.0 style."""
    pass


engine = create_engine(
    str(settings.database_url),     # ← coerce here
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.sql_echo,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,       # Keeps objects usable after commit — important for FastAPI response serialization
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency. Yields a session and guarantees rollback + close on exception."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()