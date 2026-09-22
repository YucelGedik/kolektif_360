"""PLC-HMI-20260922-18 (HMI-A01, C06_1 audit): `set_parameter` only checked
`move_to_start_busy` - cycle_active, stale data, a disconnected PLC, an
in-flight jog, or a still-moving axis could all let a write reach the real
PLC even though the UI (SettingsPage) would normally have blocked the
Apply button. Reproduction from the audit report: cycle_active=True +
stale=True + DISCONNECTED while calling set_parameter() still reached the
worker. These tests lock in the fix - each bad condition alone must refuse
the write (cache/local value unchanged), and a clean state must still work."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from core.models import ConnectionState
from services.machine_service import MachineService


def _real_service(tmp_path) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(
        json.dumps({"endpoint": "opc.tcp://192.168.0.2:4840", "nodes": {}}), encoding="utf-8"
    )
    svc = MachineService(config_path=cfg)
    svc._worker = MagicMock()
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.stale = False
    return svc


def test_audit_repro_cycle_active_stale_disconnected_refuses_write(tmp_path):
    """Exact HMI-A01 reproduction from the audit report."""
    svc = _real_service(tmp_path)
    svc.snapshot.cycle_active = True
    svc.snapshot.stale = True
    svc.snapshot.connection_state = ConnectionState.DISCONNECTED
    before = svc.get_parameter_value("lr_x_jog_velocity")

    with pytest.raises(ValueError):
        svc.set_parameter("lr_x_jog_velocity", 20.0)

    svc._worker.request_write.assert_not_called()
    assert svc.get_parameter_value("lr_x_jog_velocity") == before


def test_write_refused_while_cycle_active(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.cycle_active = True

    with pytest.raises(ValueError):
        svc.set_parameter("lr_x_cut_velocity", 100.0)
    svc._worker.request_write.assert_not_called()


def test_write_refused_while_stale(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.stale = True

    with pytest.raises(ValueError):
        svc.set_parameter("lr_x_cut_velocity", 100.0)
    svc._worker.request_write.assert_not_called()


def test_write_refused_while_disconnected(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.connection_state = ConnectionState.DISCONNECTED

    with pytest.raises(ValueError):
        svc.set_parameter("lr_x_cut_velocity", 100.0)
    svc._worker.request_write.assert_not_called()


def test_write_refused_while_jogging(tmp_path):
    svc = _real_service(tmp_path)
    svc._jog_x_active = True  # bypass jog_x()'s own manual-mode gating

    with pytest.raises(ValueError):
        svc.set_parameter("lr_x_cut_velocity", 100.0)
    svc._worker.request_write.assert_not_called()


def test_write_refused_while_axis_still_moving(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.y_actual_vel = 5.0  # above AXIS_STOPPED_VELOCITY_TOLERANCE

    with pytest.raises(ValueError):
        svc.set_parameter("lr_x_cut_velocity", 100.0)
    svc._worker.request_write.assert_not_called()


def test_write_allowed_in_a_clean_state(tmp_path):
    svc = _real_service(tmp_path)

    svc.set_parameter("lr_x_cut_velocity", 100.0)

    svc._worker.request_write.assert_called_once()


def test_write_still_allowed_in_demo_mode_ignoring_connection_state(tmp_path):
    """Demo mode has no real connection to be stale/disconnected about -
    only cycle_active/jog/axis-motion should still gate it there."""
    cfg = tmp_path / "opcua.json"
    cfg.write_text(json.dumps({"endpoint": "", "nodes": {}}), encoding="utf-8")
    svc = MachineService(config_path=cfg)
    assert svc.demo_mode is True

    svc.set_parameter("lr_x_cut_velocity", 100.0)

    assert svc.get_parameter_value("lr_x_cut_velocity") == 100.0
