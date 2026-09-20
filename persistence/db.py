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
    _migrate_alarm_events_severity(_engine)
    _SessionFactory = sessionmaker(bind=_engine, future=True, expire_on_commit=False)
    return _engine


def _migrate_alarm_events_severity(engine) -> None:
    """`create_all()` only creates missing TABLES, not missing COLUMNS on
    existing ones - an existing local `data/bufera.db` from before the
    2026-09-18 Alarm/Uyarı/Mesaj model change would be missing `severity`
    and `code` would no longer be NOT NULL. Add the column if absent so old
    databases keep working without the user having to delete their history."""
    with engine.connect() as conn:
        columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(alarm_events)")}
        if columns and "severity" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE alarm_events ADD COLUMN severity VARCHAR(16) DEFAULT 'ALARM'"
            )
            conn.commit()


def get_session() -> Session:
    if _SessionFactory is None:
        init_engine()
    assert _SessionFactory is not None
    return _SessionFactory()
