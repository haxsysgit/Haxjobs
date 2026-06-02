from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from haxjobs_api.config import get_settings


class Base(DeclarativeBase):
    """Shared SQLAlchemy base for future HaxJobs models."""


def create_database_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine with SQLite-friendly defaults."""

    resolved_url = database_url or get_settings().database_url
    connect_args = {"check_same_thread": False} if resolved_url.startswith("sqlite") else {}
    return create_engine(resolved_url, connect_args=connect_args, future=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


engine = create_database_engine()
SessionLocal = create_session_factory(engine)


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency that provides one database session per request."""

    with SessionLocal() as session:
        yield session
