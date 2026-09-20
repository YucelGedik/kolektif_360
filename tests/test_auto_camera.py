"""PLC-HMI-20260917-03: tam otomatik masa testi kamera emülatörü. Kullanıcı
tek tek paket/CutPermit/ZDownRequest tıklamak istemiyor - `start_auto_camera`
sonrası `_on_auto_camera_tick`, PLC state'ini (cycle_state, xTrajectoryValid/
Fault) ve actual X'i izleyerek Faz C tablosundaki davranışı üretmeli. Gerçek
bir PLC'ye bağlanılmaz - gerçek mod bir `MagicMock` worker ile taklit edilir."""

from __future__ import annotations

from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication

# QTimer.isActive() only reports correctly once a QCoreApplication exists in
# the thread (confirmed empirically: without one, .start() is accepted but
# isActive() stays False forever) - this module asserts on heartbeat_active/
# auto_timer.isActive(), so make sure one exists. Harmless/idempotent: Qt
# only allows one QApplication per process, other test modules that never
# needed one are unaffected.
_app = QApplication.instance() or QApplication([])

from core.cycle_state import CycleState
from core.models import ConnectionState
from services.machine_service import MachineService
from services.vision_simulator import (
    MIN_LEAD_DISTANCE_MM,
    VisionSimulatorService,
)


def _armed(tmp_path) -> tuple[MachineService, VisionSimulatorService]:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(
        '{"endpoint": "opc.tcp://192.168.0.2:4840", "vision_simulator_enabled": true, "nodes": {}}',
        encoding="utf-8",
    )
    svc = MachineService(config_path=cfg)
    svc._worker = MagicMock()
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.stale = False
    sim = VisionSimulatorService(svc)
    ok, reason = sim.arm()
    assert ok, reason
    return svc, sim


def _cut_permit_calls(svc: MachineService) -> list[bool]:
    return [
        call.args[1]
        for call in svc._worker.request_write.call_args_list
        if call.args[0] == "vision_cut_permit"
    ]


def _z_down_calls(svc: MachineService) -> list[bool]:
    return [
        call.args[1]
        for call in svc._worker.request_write.call_args_list
        if call.args[0] == "vision_z_down_request"
    ]


def _sequence_values(svc: MachineService) -> list[int]:
    values = []
    for call in svc._worker.request_write_sequence.call_args_list:
        fields = call.args[0]
        values.append(dict(fields)["vision_sequence"])
    return values


def test_start_auto_camera_requires_armed(tmp_path):
    cfg = tmp_path / "opcua.json"
    cfg.write_text('{"endpoint": "", "vision_simulator_enabled": true, "nodes": {}}', encoding="utf-8")
    svc = MachineService(config_path=cfg)
    sim = VisionSimulatorService(svc)

    ok, reason = sim.start_auto_camera()

    assert ok is False
    assert sim.auto_camera_active is False


def test_start_auto_camera_writes_happy_path_booleans_once(tmp_path):
    svc, sim = _armed(tmp_path)

    ok, reason = sim.start_auto_camera()

    assert ok, reason
    svc._worker.request_write.assert_any_call("vision_ready", True)
    svc._worker.request_write.assert_any_call("vision_fault", False)
    svc._worker.request_write.assert_any_call("line_valid", True)
    # Yalnız oturum başında bir kez - tick'lerde tekrar tekrar değil.
    ready_calls = [c for c in svc._worker.request_write.call_args_list if c.args[0] == "vision_ready"]
    assert len(ready_calls) == 1
    sim._on_auto_camera_tick()
    sim._on_auto_camera_tick()
    ready_calls_after = [c for c in svc._worker.request_write.call_args_list if c.args[0] == "vision_ready"]
    assert len(ready_calls_after) == 1


def test_start_auto_camera_also_starts_heartbeat(tmp_path):
    """Gerçek kullanıcı raporu (2026-09-17): 'otomatik başlattım ama
    heartbeat üretmedi' - xVisionHeartbeatOK hiç TRUE olmuyordu çünkü
    start_auto_camera() heartbeat'i hiç başlatmıyordu, sadece manuel
    kutuyu devre dışı bırakıyordu. Bu artık otomatik başlamalı."""
    svc, sim = _armed(tmp_path)

    ok, reason = sim.start_auto_camera()

    assert ok, reason
    assert sim.heartbeat_active is True
    svc._worker.reset_mock()
    sim._on_heartbeat_tick()
    svc._worker.request_write.assert_called_once_with("vision_heartbeat", 1)


def test_stop_auto_camera_also_stops_heartbeat(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()
    assert sim.heartbeat_active is True

    sim.stop_auto_camera()

    assert sim.heartbeat_active is False


def test_disarm_stops_heartbeat_started_by_auto_camera(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()

    sim.disarm()

    assert sim.heartbeat_active is False


def test_wait_for_material_no_permit_no_packet(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()
    svc.snapshot.cycle_state = int(CycleState.WAIT_FOR_MATERIAL)

    sim._on_auto_camera_tick()

    assert _cut_permit_calls(svc) in ([], [False])
    assert _z_down_calls(svc) in ([], [False])
    svc._worker.request_write_sequence.assert_not_called()


def test_clamp_down_still_no_permit(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()
    svc.snapshot.cycle_state = int(CycleState.CLAMP_DOWN)

    sim._on_auto_camera_tick()

    assert True not in _cut_permit_calls(svc)
    svc._worker.request_write_sequence.assert_not_called()


def test_wait_vision_sends_fresh_packet_and_permit_true(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()
    svc.snapshot.x_actual_pos = 10.0
    svc.snapshot.cycle_state = int(CycleState.WAIT_VISION)

    sim._on_auto_camera_tick()

    assert _cut_permit_calls(svc) == [True]
    assert _z_down_calls(svc) in ([], [False])
    svc._worker.request_write_sequence.assert_called_once()
    (fields,), _ = svc._worker.request_write_sequence.call_args
    tags = [t for t, _v in fields]
    assert tags == [
        "vision_target_x",
        "vision_target_y",
        "vision_ready",
        "line_valid",
        "vision_fault",
        "vision_sequence",
    ]
    target_x = dict(fields)["vision_target_x"]
    assert target_x - 10.0 >= MIN_LEAD_DISTANCE_MM


def test_wait_blade_request_zdown_only_when_trajectory_valid(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()
    svc.snapshot.cycle_state = int(CycleState.WAIT_BLADE_REQUEST)
    svc.snapshot.trajectory_valid = False
    svc.snapshot.trajectory_fault = False

    sim._on_auto_camera_tick()
    assert _z_down_calls(svc) == [False]

    svc._worker.reset_mock()
    svc.snapshot.trajectory_valid = True
    sim._on_auto_camera_tick()
    assert _z_down_calls(svc) == [True]


def test_wait_blade_request_zdown_false_if_trajectory_fault(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()
    svc.snapshot.cycle_state = int(CycleState.WAIT_BLADE_REQUEST)
    svc.snapshot.trajectory_valid = True
    svc.snapshot.trajectory_fault = True

    sim._on_auto_camera_tick()

    assert _z_down_calls(svc) == [False]


def test_blade_down_holds_zdown_true_regardless_of_trajectory_flags(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()
    # Sticky: WAIT_BLADE_REQUEST'te zaten TRUE yapıldı varsayımıyla BLADE_DOWN'a giriliyor.
    svc.snapshot.cycle_state = int(CycleState.BLADE_DOWN)
    svc.snapshot.trajectory_valid = False  # BLADE_DOWN'da bu artık önemli değil
    svc.snapshot.trajectory_fault = True

    sim._on_auto_camera_tick()

    assert _z_down_calls(svc) == [True]


def test_blade_down_does_not_flicker_zdown_false_across_ticks(tmp_path):
    """Görev notu: 'aktif talebi kısa aralıklarla yanlışlıkla FALSE yapma'."""
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()
    svc.snapshot.cycle_state = int(CycleState.BLADE_DOWN)

    sim._on_auto_camera_tick()
    svc._worker.reset_mock()
    sim._on_auto_camera_tick()  # aynı state, aynı değer - tekrar yazma

    assert _z_down_calls(svc) == []


def test_cutting_refreshes_target_as_actual_x_advances(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()
    svc.snapshot.cycle_state = int(CycleState.CUTTING)
    svc.snapshot.x_actual_pos = 100.0

    sim._on_auto_camera_tick()
    assert svc._worker.request_write_sequence.call_count == 1
    svc.visionSequentialWriteResult.emit(True, "")  # PLC bir önceki paketi onayladı

    # Az hareket (epsilon altı) -> yeni paket YOK.
    svc.snapshot.x_actual_pos = 100.1
    sim._on_auto_camera_tick()
    assert svc._worker.request_write_sequence.call_count == 1

    # Anlamlı hareket (epsilon üstü) -> yeni paket, sequence artar.
    svc.snapshot.x_actual_pos = 105.0
    sim._on_auto_camera_tick()
    assert svc._worker.request_write_sequence.call_count == 2

    seqs = _sequence_values(svc)
    assert seqs[1] == seqs[0] + 1


def test_blade_up_and_return_states_no_permit_no_new_packet(tmp_path):
    for state in (CycleState.BLADE_UP, CycleState.RETURN_AXES, CycleState.CLAMP_UP, CycleState.CYCLE_COMPLETE):
        svc, sim = _armed(tmp_path)
        sim.start_auto_camera()
        svc.snapshot.cycle_state = int(state)

        sim._on_auto_camera_tick()

        assert True not in _cut_permit_calls(svc), state
        assert True not in _z_down_calls(svc), state
        svc._worker.request_write_sequence.assert_not_called()


def test_stopping_fault_recovery_manual_no_permit_no_zdown(tmp_path):
    for state in (CycleState.STOPPING, CycleState.FAULT, CycleState.RECOVERY, CycleState.MANUAL):
        svc, sim = _armed(tmp_path)
        sim.start_auto_camera()
        svc.snapshot.cycle_state = int(state)

        sim._on_auto_camera_tick()

        assert True not in _cut_permit_calls(svc), state
        assert True not in _z_down_calls(svc), state


def test_stale_snapshot_generates_nothing(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()
    svc._worker.reset_mock()
    svc.snapshot.stale = True
    svc.snapshot.cycle_state = int(CycleState.WAIT_VISION)

    sim._on_auto_camera_tick()

    svc._worker.request_write.assert_not_called()
    svc._worker.request_write_sequence.assert_not_called()


def test_disarm_stops_auto_camera(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()
    assert sim.auto_camera_active is True

    sim.disarm()

    assert sim.auto_camera_active is False
    assert sim._auto_timer.isActive() is False


def test_reconnect_force_disarm_stops_auto_camera(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()

    svc.connectionStateChanged.emit(ConnectionState.ERROR)

    assert sim.auto_camera_active is False
    assert sim._auto_timer.isActive() is False


def test_period_cannot_change_while_active(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera(period_ms=100)

    ok, reason = sim.set_auto_camera_period_ms(200)

    assert ok is False
    assert sim.auto_camera_period_ms == 100


def test_lead_distance_has_a_floor_at_low_velocity(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.set_parameter("lr_x_cut_velocity", 1.0)  # very slow
    sim.start_auto_camera(period_ms=100)

    lead = sim._compute_lead_distance_mm()

    assert lead == MIN_LEAD_DISTANCE_MM


def test_lead_distance_scales_with_velocity_and_period(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.set_parameter("lr_x_cut_velocity", 175.0)
    sim.start_auto_camera(period_ms=100)

    lead = sim._compute_lead_distance_mm()

    assert lead == 175.0 * 0.1 * 5  # velocity * period_s * margin


def test_disarm_actually_cancels_pending_worker_write(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.send_packet(target_x=10.0, target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False)

    sim.disarm()

    svc._worker.cancel_pending_sequence.assert_called_once()


def test_force_disarm_actually_cancels_pending_worker_write(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.send_packet(target_x=10.0, target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False)

    svc.connectionStateChanged.emit(ConnectionState.ERROR)

    svc._worker.cancel_pending_sequence.assert_called_once()
