"""Faz 1 (PLC -> HMI read binding) derivation tests, updated per the
2026-09-16 correction pass: xCycleActive and xStartPermitted are real,
authoritative PLC tags now (read directly, not derived from eMachineState)
per the task plan. X/Y servo-ready AND-NOT derivation, ClampDown/BladeZDown
"up" derivation and the corrected cut-progress formula are unchanged.

Faz 2 additions: set_manual_mode / release_all_jog demo-mode behavior.
"""

from __future__ import annotations

from services.machine_service import MachineService


def _service() -> MachineService:
    # _on_raw_snapshot itself does not depend on demo_mode, so this is a
    # safe, connection-free host for exercising the pure raw-dict ->
    # MachineSnapshot mapping regardless of what config/opcua.json's live
    # (locally-customized, possibly real) endpoint currently is.
    return MachineService()


def _demo_service(tmp_path) -> MachineService:
    # Tests that DO care about demo_mode must not depend on config/opcua.json
    # (a live, locally-customized file that may legitimately hold a real PLC
    # endpoint) - point at an isolated, guaranteed-empty-endpoint config.
    cfg = tmp_path / "opcua.json"
    cfg.write_text('{"endpoint": "", "nodes": {}}', encoding="utf-8")
    return MachineService(config_path=cfg)


def test_servo_ready_is_power_status_and_not_power_error():
    svc = _service()
    svc._on_raw_snapshot({"x_power_status": True, "x_power_error": False})
    assert svc.snapshot.x_servo_ready is True
    assert svc.snapshot.x_fault is False

    svc._on_raw_snapshot({"x_power_status": True, "x_power_error": True})
    assert svc.snapshot.x_servo_ready is False
    assert svc.snapshot.x_fault is True


def test_clamp_and_blade_up_are_derived_not_read():
    svc = _service()
    svc._on_raw_snapshot({"clamp_down": True, "blade_down": False})
    assert svc.snapshot.clamp_down is True
    assert svc.snapshot.clamp_up is False
    assert svc.snapshot.blade_down is False
    assert svc.snapshot.blade_up is True


def test_auto_mode_is_derived_from_manual_mode():
    svc = _service()
    svc._on_raw_snapshot({"manual_mode": True})
    assert svc.snapshot.auto_mode is False
    svc._on_raw_snapshot({"manual_mode": False})
    assert svc.snapshot.auto_mode is True


def test_cycle_active_and_start_permitted_are_read_directly_not_derived():
    """PLC is authoritative for both; HMI must not recompute them from
    eMachineState (2026-09-16 duzeltmesi)."""
    svc = _service()
    svc._on_raw_snapshot({"cycle_active": True, "start_permitted": False})
    assert svc.snapshot.cycle_active is True
    assert svc.snapshot.start_permitted is False

    svc._on_raw_snapshot({"cycle_active": False, "start_permitted": True})
    assert svc.snapshot.cycle_active is False
    assert svc.snapshot.start_permitted is True


def test_x_at_start_and_y_at_center_are_diagnostic_reads():
    svc = _service()
    svc._on_raw_snapshot({"x_at_start": True, "y_at_center": False})
    assert svc.snapshot.x_at_start is True
    assert svc.snapshot.y_at_center is False


def test_cycle_progress_uses_cut_start_and_cut_end_x():
    svc = _service()
    svc._on_raw_snapshot(
        {
            "x_actual_pos": 900.0,
            "lr_x_cut_start_pos": 0.0,
            "cut_end_x": 3600.0,
        }
    )
    assert svc.snapshot.cycle_progress == 25.0


def test_cycle_progress_is_clamped_to_0_100():
    svc = _service()
    svc._on_raw_snapshot(
        {"x_actual_pos": -50.0, "lr_x_cut_start_pos": 0.0, "cut_end_x": 3600.0}
    )
    assert svc.snapshot.cycle_progress == 0.0

    svc._on_raw_snapshot(
        {"x_actual_pos": 5000.0, "lr_x_cut_start_pos": 0.0, "cut_end_x": 3600.0}
    )
    assert svc.snapshot.cycle_progress == 100.0


def test_set_manual_mode_flips_demo_simulator_mode(tmp_path):
    svc = _demo_service(tmp_path)
    assert svc.demo_mode is True
    # Gerçek çalışmada service.start() bunu False yapar (Demo modda bağlantı
    # kavramı yok); burada elle taklit ediliyor - aksi halde H2'nin yeni
    # "stale/bilinmeyen durumda fail-closed" engeli (2026-09-18) bunu da
    # reddeder, ki bu testin amacı değil.
    svc.snapshot.stale = False

    svc.set_manual_mode(True)
    assert svc._demo.manual_mode is True
    assert svc._demo.auto_mode is False

    svc.set_manual_mode(False)
    assert svc._demo.manual_mode is False
    assert svc._demo.auto_mode is True


def test_release_all_jog_stops_demo_jog(tmp_path):
    svc = _demo_service(tmp_path)
    svc.snapshot.manual_mode = True  # let _manual_allowed() pass for this test
    svc.jog_x(1, True)
    svc.jog_y(-1, True)
    assert svc._demo.jog_x_dir == 1
    assert svc._demo.jog_y_dir == -1

    svc.release_all_jog()
    assert svc._demo.jog_x_dir == 0
    assert svc._demo.jog_y_dir == 0


def _real_mode_service(tmp_path) -> MachineService:
    # A non-empty endpoint -> demo_mode False, without actually starting the
    # worker/event loop (start() is never called in these tests).
    cfg = tmp_path / "opcua.json"
    cfg.write_text(
        '{"endpoint": "opc.tcp://192.168.0.2:4840", "nodes": {}}', encoding="utf-8"
    )
    return MachineService(config_path=cfg)


def test_parameters_are_not_confirmed_until_read_from_real_plc(tmp_path):
    """2026-09-16: Settings screen must never show a default/local-cache
    value as if it were real PLC data."""
    svc = _real_mode_service(tmp_path)
    assert svc.demo_mode is False
    assert svc.is_parameter_confirmed("lr_x_cut_velocity") is False

    svc._on_raw_snapshot({"lr_x_cut_velocity": 180.0})
    assert svc.is_parameter_confirmed("lr_x_cut_velocity") is True
    assert svc.get_parameter_value("lr_x_cut_velocity") == 180.0
    # A parameter that hasn't come back yet must still read as unconfirmed.
    assert svc.is_parameter_confirmed("lr_y_center_position") is False


def test_all_parameters_are_pre_confirmed_in_demo_mode(tmp_path):
    svc = _demo_service(tmp_path)
    assert svc.demo_mode is True
    assert svc.is_parameter_confirmed("lr_x_cut_velocity") is True
    assert svc.is_parameter_confirmed("t_vision_heartbeat_timeout") is True
