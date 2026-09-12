"""SQLite-backed persistence for alarm history and engineering parameter
overrides. Kept separate from the PLC/OPC UA layer: this is local HMI
history, not the machine's source of truth (the PLC is)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = DATA_DIR / "bufera.db"


class Base(DeclarativeBase):
    pass


_engine = None
_SessionFactory: sessionmaker[Session] | None = None


def init_engine(db_path: Path | str | None = None):
    global _engine, _SessionFactory
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(f"sqlite:///{path}", future=True)

    # Import models so they register on Base.metadata before create_all.
    import persistence.alarms  # noqa: F401
    import persistence.settings_store  # noqa: F401

    Base.metadata.create_all(_engine)
    _SessionFactory = sessionmaker(bind=_engine, future=True, expire_on_commit=False)
    return _engine


def get_session() -> Session:
    if _SessionFactory is None:
        init_engine()
    assert _SessionFactory is not None
    return _SessionFactory()
