"""Local key/value store for engineering parameter overrides (brief section
8/13/24: X/Y motion params, timeouts, delays). This is a convenience cache
for the Settings screen; when OPC UA is connected, a write should still go
to the PLC `PAR_*` tags and be read back for verification — this store just
lets the demo/engineering UI remember edited values across restarts."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from persistence.db import Base, get_session


class EngineeringSetting(Base):
    __tablename__ = "engineering_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now)


class SettingsStore:
    def get_all(self) -> dict[str, str]:
        with get_session() as session:
            rows = session.query(EngineeringSetting).all()
            return {row.key: row.value for row in rows}

    def set(self, key: str, value: str) -> None:
        with get_session() as session:
            row = session.get(EngineeringSetting, key)
            if row is None:
                row = EngineeringSetting(key=key, value=value)
                session.add(row)
            else:
                row.value = value
                row.updated_at = dt.datetime.now()
            session.commit()
