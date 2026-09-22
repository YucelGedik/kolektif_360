"""PLC-HMI-20260922-18 (HMI-A02, C06_1 audit): `MachineService._active_
alarm_events` lives only in RAM and starts empty on every restart, but the
underlying SQLite alarm history is persistent. Without reconciliation:
- a condition that resolved while the app was closed never gets its DB
  row closed (the new service instance has no memory the row exists, so
  the falling edge is never observed);
- a condition that is STILL true on restart gets a duplicate row logged.

Audit reproduction: "servisA x_power_error=True -> aktif1; aynı testDB ile
servisB x_power_error=False -> aktif hâlâ1." These tests use two separate
MachineService instances against the SAME isolated DB file to reproduce a
real app restart."""

from __future__ import annotations

import contextlib
import json
from unittest.mock import MagicMock

import persistence.db as db_module
from services.machine_service import MachineService


@contextlib.contextmanager
def _isolated_engine(tmp_path):
    db_module.init_engine(tmp_path / "test_alarm_restart_reconciliation.db")
    try:
        yield
    finally:
        db_module.init_engine()


def _real_service(tmp_path) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(
        json.dumps({"endpoint": "opc.tcp://192.168.0.2:4840", "nodes": {}}), encoding="utf-8"
    )
    svc = MachineService(config_path=cfg)
    svc._worker = MagicMock()
    return svc


def test_audit_repro_condition_resolved_while_app_was_closed(tmp_path):
    with _isolated_engine(tmp_path):
        service_a = _real_service(tmp_path)
        service_a._on_raw_snapshot({"x_power_error": True})
        assert service_a.active_alarm_count() == 1

        # "restart": a brand new MachineService instance, same DB, RAM dict empty.
        service_b = _real_service(tmp_path)
        assert service_b._active_alarm_events == {}  # confirms the RAM reset

        service_b._on_raw_snapshot({"x_power_error": False})  # PLC now reports resolved

        assert service_b.active_alarm_count() == 0
        # Geçmişte kalmalı - silinmedi, yalnız kapandı.
        assert len(service_b.recent_alarms()) == 1
        assert service_b.recent_alarms()[0].active is False


def test_condition_still_true_on_restart_does_not_duplicate(tmp_path):
    with _isolated_engine(tmp_path):
        service_a = _real_service(tmp_path)
        service_a._on_raw_snapshot({"x_power_error": True})
        assert service_a.active_alarm_count() == 1

        service_b = _real_service(tmp_path)
        service_b._on_raw_snapshot({"x_power_error": True})  # hâlâ TRUE

        assert service_b.active_alarm_count() == 1  # NOT 2 - no duplicate row
        assert len(service_b.recent_alarms()) == 1


def test_reconciled_alarm_still_clears_correctly_afterwards(tmp_path):
    """After reconciliation adopts an old open row, the normal falling-edge
    path must keep working for it (not just the one-time reconciliation)."""
    with _isolated_engine(tmp_path):
        service_a = _real_service(tmp_path)
        service_a._on_raw_snapshot({"x_power_error": True})

        service_b = _real_service(tmp_path)
        service_b._on_raw_snapshot({"x_power_error": True})  # adopted via reconciliation
        assert service_b.active_alarm_count() == 1

        service_b._on_raw_snapshot({"x_power_error": False})

        assert service_b.active_alarm_count() == 0


def test_reconciliation_runs_only_once_per_service_instance(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)
        assert svc._alarm_state_reconciled is False

        svc._on_raw_snapshot({"x_power_error": True})

        assert svc._alarm_state_reconciled is True
        svc._on_raw_snapshot({"x_power_error": True})  # second call - no crash, no duplicate
        assert svc.active_alarm_count() == 1


def test_pre_existing_duplicate_open_rows_are_cleaned_up_keeping_the_newest(tmp_path):
    """A hypothetical leftover from before this fix existed: two open rows
    for the same catalog_id. Reconciliation must not just silently ignore
    the older one - it should close it (clear_event, not delete) so the
    active list/count reflects a single, correct entry."""
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)
        older = svc._alarms.log_event("ALARM", "X AXIS", "eski kopya", catalog_id="H06")
        newer = svc._alarms.log_event("ALARM", "X AXIS", "X servo etkinleştirme hatası.", catalog_id="H06")
        assert svc._alarms.active_count() == 2  # both still open before reconciliation

        svc._on_raw_snapshot({"x_power_error": True})

        assert svc.active_alarm_count() == 1
        assert svc._active_alarm_events["H06"] == newer.id
        recent = {e.id: e for e in svc.recent_alarms()}
        assert recent[older.id].active is False  # closed, not deleted
        assert recent[newer.id].active is True


def test_active_alarm_count_is_not_hidden_by_the_100_row_history_cap(tmp_path):
    """HMI-A02, second finding: `recent(limit=100)` is a fine bound for the
    history view, but the active count/list must never depend on it - an
    old-but-still-active alarm must not vanish once 100+ other (mostly
    cleared) events accumulate more recently than it."""
    with _isolated_engine(tmp_path):
        svc = _real_service(tmp_path)
        svc._on_raw_snapshot({"x_power_error": True})  # the one alarm that stays active
        assert svc.active_alarm_count() == 1

        # Push 100 unrelated, immediately-cleared events so the still-active
        # one falls outside a plain `recent(limit=100)` window.
        for _ in range(100):
            svc._on_raw_snapshot({"y_power_error": True})
            svc._on_raw_snapshot({"y_power_error": False})

        assert svc.active_alarm_count() == 1
        assert any(e.severity == "ALARM" and e.active for e in svc.active_alarms())
