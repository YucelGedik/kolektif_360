"""SQLite-backed persistence for alarm history and engineering parameter
overrides. Kept separate from the PLC/OPC UA layer: this is local HMI
history, not the machine's source of truth (the PLC is)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.paths import data_dir


def default_db_path() -> Path:
    """Where the alarm history lives. Writable in a frozen install too."""
    return data_dir() / "bufera.db"


class Base(DeclarativeBase):
    pass


_engine = None
_SessionFactory: sessionmaker[Session] | None = None


def init_engine(db_path: Path | str | None = None):
    global _engine, _SessionFactory
    path = Path(db_path) if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(f"sqlite:///{path}", future=True)

    # Import models so they register on Base.metadata before create_all.
    import persistence.alarms  # noqa: F401
    import persistence.settings_store  # noqa: F401

    Base.metadata.create_all(_engine)
    _migrate_alarm_events_severity(_engine)
    _migrate_alarm_events_code_nullable(_engine)
    _migrate_alarm_events_catalog_id(_engine)
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


def _migrate_alarm_events_code_nullable(engine) -> None:
    """PLC-HMI-20260921-16: the C6.1 alarm-condition catalog logs entries
    with `code=None` (the catalog ID is a document reference, not a PLC
    alarm number - see `persistence/alarms.py`). The ORM model has always
    declared `code` nullable, but a `data/bufera.db` created before that
    still has the original `NOT NULL` constraint physically on disk -
    `create_all()`/simple `ALTER TABLE ... ADD COLUMN` cannot loosen an
    existing constraint in SQLite, so this rebuilds the table (copy, drop,
    rename) only when the live schema is still NOT NULL. No data is lost."""
    with engine.connect() as conn:
        info = list(conn.exec_driver_sql("PRAGMA table_info(alarm_events)"))
        if not info:
            return  # table doesn't exist yet - create_all() already made it right
        code_column = next((row for row in info if row[1] == "code"), None)
        if code_column is None or not code_column[3]:  # index 3 = notnull flag
            return
        conn.exec_driver_sql("ALTER TABLE alarm_events RENAME TO alarm_events_pre_nullable_code")
        conn.exec_driver_sql(
            """
            CREATE TABLE alarm_events (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                occurred_at DATETIME,
                cleared_at DATETIME,
                code INTEGER,
                source VARCHAR(32) NOT NULL,
                message VARCHAR(200) NOT NULL,
                severity VARCHAR(16)
            )
            """
        )
        conn.exec_driver_sql(
            "INSERT INTO alarm_events (id, occurred_at, cleared_at, code, source, message, severity) "
            "SELECT id, occurred_at, cleared_at, code, source, message, severity "
            "FROM alarm_events_pre_nullable_code"
        )
        conn.exec_driver_sql("DROP TABLE alarm_events_pre_nullable_code")
        conn.commit()


def _migrate_alarm_events_catalog_id(engine) -> None:
    """PLC-HMI-20260922-18 (HMI-A02, C06_1 audit): `_active_alarm_events`
    (RAM only) can no longer be the sole record of which catalog entry
    (H01, H20, ...) a persisted, still-open row belongs to - after a
    restart that dict is empty and a stuck/duplicate active alarm can
    result. Persist the catalog id too so the service can reconcile
    against the real DB on startup (`MachineService._reconcile_alarm_
    state_with_persisted_events`). A nullable ADD COLUMN needs no table
    rebuild in SQLite (unlike loosening a NOT NULL constraint)."""
    with engine.connect() as conn:
        columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(alarm_events)")}
        if columns and "catalog_id" not in columns:
            conn.exec_driver_sql("ALTER TABLE alarm_events ADD COLUMN catalog_id VARCHAR(8)")
            conn.commit()


def get_session() -> Session:
    if _SessionFactory is None:
        init_engine()
    assert _SessionFactory is not None
    return _SessionFactory()
