"""2026-09-16 real-PLC bug report: Settings screen showed "✓ UYGULANDI"
immediately on Apply, before the PLC had actually accepted the write - the
next 100ms read tick would then silently revert the value while the status
label kept lying about success. These tests cover the fix: a write is only
"confirmed" once a later read of the same tag echoes the written value back,
and only reported as failed after a timeout with no such echo.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import services.machine_service as machine_service_module
from core.models import ConnectionState
from services.machine_service import MachineService


def _real_mode_service(tmp_path) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(
        '{"endpoint": "opc.tcp://192.168.0.2:4840", "nodes": {}}', encoding="utf-8"
    )
    svc = MachineService(config_path=cfg)
    # start() is never called in these tests (no real network connection);
    # a fake worker stands in so set_parameter() takes its "connected, real
    # PLC write in flight" branch instead of failing immediately for having
    # no worker at all.
    svc._worker = MagicMock()
    # PLC-HMI-20260922-18 (HMI-A01): set_parameter now refuses writes while
    # disconnected/stale (real-mode default) - mark this fixture as a
    # genuinely connected, fresh service, matching every other real-mode
    # fixture in the suite (e.g. test_move_to_start.py::_real_service).
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.stale = False
    return svc


def test_set_parameter_does_not_confirm_before_plc_echoes_it_back(tmp_path):
    svc = _real_mode_service(tmp_path)
    svc._on_raw_snapshot({"lr_x_cut_velocity": 175.0})  # initial confirmed read

    confirmed_events: list[str] = []
    failed_events: list[str] = []
    svc.parameterWriteConfirmed.connect(confirmed_events.append)
    svc.parameterWriteFailed.connect(failed_events.append)

    svc.set_parameter("lr_x_cut_velocity", 180.0)

    # Optimistic local value shown immediately...
    assert svc.get_parameter_value("lr_x_cut_velocity") == 180.0
    # ...but NOT reported as confirmed yet - no echo from the PLC.
    assert confirmed_events == []
    assert failed_events == []


def test_set_parameter_confirms_once_plc_echoes_written_value(tmp_path):
    svc = _real_mode_service(tmp_path)
    svc._on_raw_snapshot({"lr_x_cut_velocity": 175.0})

    confirmed_events: list[str] = []
    svc.parameterWriteConfirmed.connect(confirmed_events.append)

    svc.set_parameter("lr_x_cut_velocity", 180.0)
    svc._on_raw_snapshot({"lr_x_cut_velocity": 180.0})  # PLC now reports the new value

    assert confirmed_events == ["lr_x_cut_velocity"]
    assert svc.get_parameter_value("lr_x_cut_velocity") == 180.0


def test_stale_read_during_pending_window_does_not_revert_or_fail(tmp_path):
    """The bug: a read that arrives before the PLC processed the write must
    not be mistaken for a rejection and must not clobber the optimistic
    value while still inside the confirmation window."""
    svc = _real_mode_service(tmp_path)
    svc._on_raw_snapshot({"lr_x_cut_velocity": 175.0})

    confirmed_events: list[str] = []
    failed_events: list[str] = []
    svc.parameterWriteConfirmed.connect(confirmed_events.append)
    svc.parameterWriteFailed.connect(failed_events.append)

    svc.set_parameter("lr_x_cut_velocity", 180.0)
    svc._on_raw_snapshot({"lr_x_cut_velocity": 175.0})  # stale read, write still in flight

    assert confirmed_events == []
    assert failed_events == []
    assert svc.get_parameter_value("lr_x_cut_velocity") == 180.0  # NOT reverted


def test_write_reported_as_failed_after_timeout_with_no_echo(tmp_path, monkeypatch):
    monkeypatch.setattr(machine_service_module, "PARAM_WRITE_CONFIRM_TIMEOUT_S", 0.01)
    svc = _real_mode_service(tmp_path)
    svc._on_raw_snapshot({"lr_x_cut_velocity": 175.0})

    failed_events: list[str] = []
    svc.parameterWriteFailed.connect(failed_events.append)

    svc.set_parameter("lr_x_cut_velocity", 180.0)
    time.sleep(0.02)
    svc._on_raw_snapshot({"lr_x_cut_velocity": 175.0})  # PLC still reports the old value

    assert failed_events == ["lr_x_cut_velocity"]
    # We trust the PLC's real value once we give up waiting, not our own guess.
    assert svc.get_parameter_value("lr_x_cut_velocity") == 175.0


def test_on_error_emits_parameter_write_error_for_a_pending_write(tmp_path):
    """2026-09-18 bug report: the generic "HATA — PLC onaylamadı" message
    hid a real OPC UA rejection. `_on_error` must recognize the worker's
    "Write failed for '<tag>': <reason>" message and, if that tag is
    currently a pending parameter write, surface the real reason via
    `parameterWriteError` - the same class of fix already made for the
    Vision simulator's sequential writes."""
    svc = _real_mode_service(tmp_path)
    svc._on_raw_snapshot({"lr_x_cut_velocity": 175.0})

    errors: list[tuple[str, str]] = []
    svc.parameterWriteError.connect(lambda key, reason: errors.append((key, reason)))

    svc.set_parameter("lr_x_cut_velocity", 180.0)
    svc._on_error("Write failed for 'lr_x_cut_velocity': BadUserAccessDenied")

    assert errors == [("lr_x_cut_velocity", "BadUserAccessDenied")]


def test_on_error_ignores_failures_for_tags_with_no_pending_write(tmp_path):
    svc = _real_mode_service(tmp_path)
    svc._on_raw_snapshot({"lr_x_cut_velocity": 175.0})

    errors: list[tuple[str, str]] = []
    svc.parameterWriteError.connect(lambda key, reason: errors.append((key, reason)))

    # No set_parameter() call happened - "lr_x_cut_velocity" is not pending.
    svc._on_error("Write failed for 'lr_x_cut_velocity': BadUserAccessDenied")

    assert errors == []


def test_on_error_ignores_unrelated_messages(tmp_path):
    svc = _real_mode_service(tmp_path)
    errors: list[tuple[str, str]] = []
    svc.parameterWriteError.connect(lambda key, reason: errors.append((key, reason)))

    svc._on_error("Connection lost")  # not a "Write failed for '...'" message

    assert errors == []


def test_set_parameter_confirms_immediately_in_demo_mode(tmp_path):
    cfg = tmp_path / "opcua.json"
    cfg.write_text('{"endpoint": "", "nodes": {}}', encoding="utf-8")
    svc = MachineService(config_path=cfg)
    assert svc.demo_mode is True

    confirmed_events: list[str] = []
    svc.parameterWriteConfirmed.connect(confirmed_events.append)

    svc.set_parameter("lr_x_cut_velocity", 180.0)

    assert confirmed_events == ["lr_x_cut_velocity"]
    assert svc.get_parameter_value("lr_x_cut_velocity") == 180.0
