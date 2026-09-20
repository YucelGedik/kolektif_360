"""Faz 5: geçici Vision veri simülatörü (PLC-HMI-20260917-02) için izole
testler. Gerçek endpoint'e bağlanılmaz; her testte gerçek mod bir
`MagicMock` worker ile, demo mod ise config endpoint'i boş bırakılarak
taklit edilir. Gerçek PLC'ye kendi kendine veri göndermez."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.models import ConnectionState
from services.machine_service import VISION_SIM_WRITABLE_TAGS, MachineService
from services.vision_simulator import VisionSimulatorService


def _service(tmp_path, *, enabled: bool = True, demo: bool = False) -> MachineService:
    cfg = tmp_path / "opcua.json"
    endpoint = "" if demo else "opc.tcp://192.168.0.2:4840"
    cfg.write_text(
        '{"endpoint": "%s", "vision_simulator_enabled": %s, "nodes": {}}'
        % (endpoint, "true" if enabled else "false"),
        encoding="utf-8",
    )
    svc = MachineService(config_path=cfg)
    if not demo:
        svc._worker = MagicMock()
    return svc


def _armed(tmp_path, **kwargs) -> tuple[MachineService, VisionSimulatorService]:
    svc = _service(tmp_path, **kwargs)
    svc.snapshot.connection_state = ConnectionState.CONNECTED if not kwargs.get("demo") else ConnectionState.DEMO
    svc.snapshot.stale = False
    sim = VisionSimulatorService(svc)
    ok, reason = sim.arm()
    assert ok, reason
    return svc, sim


# -- feature flag / disarmed-by-default ------------------------------------


def test_disabled_feature_flag_blocks_arm(tmp_path):
    svc = _service(tmp_path, enabled=False)
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    sim = VisionSimulatorService(svc)

    ok, reason = sim.arm()

    assert ok is False
    assert sim.armed is False
    assert "kapalı" in reason


def test_starts_disarmed_even_when_feature_enabled(tmp_path):
    svc = _service(tmp_path, enabled=True)
    sim = VisionSimulatorService(svc)

    assert sim.armed is False
    assert sim.source == "REAL"


def test_arm_refused_while_cycle_active(tmp_path):
    svc = _service(tmp_path)
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.cycle_active = True
    sim = VisionSimulatorService(svc)

    ok, _reason = sim.arm()

    assert ok is False
    assert sim.armed is False


def test_arm_refused_while_axis_moving(tmp_path):
    svc = _service(tmp_path)
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.x_actual_vel = 12.0
    sim = VisionSimulatorService(svc)

    ok, _reason = sim.arm()

    assert ok is False


def test_arm_succeeds_and_sets_source(tmp_path):
    _svc, sim = _armed(tmp_path)

    assert sim.armed is True
    assert sim.source == "SIMULATOR"


# -- reconnect / disconnect => forced disarm, no automatic ownership -------


def test_reconnect_forces_disarm(tmp_path):
    svc, sim = _armed(tmp_path)

    svc.connectionStateChanged.emit(ConnectionState.CONNECTED)

    assert sim.armed is False
    assert sim.source == "REAL"


def test_disconnect_forces_disarm(tmp_path):
    svc, sim = _armed(tmp_path)

    svc.connectionStateChanged.emit(ConnectionState.ERROR)

    assert sim.armed is False


# -- allow-list enforcement --------------------------------------------------


def test_machine_service_rejects_writes_outside_allow_list(tmp_path):
    svc = _service(tmp_path)

    with pytest.raises(ValueError):
        svc.request_vision_write("cmd_start", True)
    with pytest.raises(ValueError):
        svc.request_vision_write("manual_mode", True)
    with pytest.raises(ValueError):
        svc.request_vision_sequential_write([("cycle_state", 80)])

    svc._worker.request_write.assert_not_called()
    svc._worker.request_write_sequence.assert_not_called()


def test_only_allow_listed_tags_are_ever_written_by_a_packet(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.x_actual_pos = 0.0

    sim.send_packet(
        target_x=1.0, target_y=0.5, vision_ready=True, line_valid=True, vision_fault=False, confidence=0.8
    )

    (fields,), _kwargs = svc._worker.request_write_sequence.call_args
    tags = {tag for tag, _value in fields}
    assert tags <= VISION_SIM_WRITABLE_TAGS


# -- packet: order, validation, in-flight serialization ----------------------


def test_send_packet_dispatches_fields_in_correct_order_with_sequence_last(tmp_path):
    svc = _service(tmp_path)
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.stale = False
    svc.snapshot.vision_sequence = 41
    sim = VisionSimulatorService(svc)
    ok, reason = sim.arm()
    assert ok, reason
    svc.snapshot.x_actual_pos = 5.0

    ok, reason = sim.send_packet(
        target_x=10.0, target_y=2.0, vision_ready=True, line_valid=True, vision_fault=False, confidence=0.9
    )

    assert ok, reason
    (fields,), _kwargs = svc._worker.request_write_sequence.call_args
    tags = [tag for tag, _value in fields]
    assert tags == [
        "vision_target_x",
        "vision_target_y",
        "vision_ready",
        "line_valid",
        "vision_fault",
        "vision_confidence",
        "vision_sequence",
    ]
    assert dict(fields)["vision_sequence"] == 42


def test_send_packet_rejects_target_x_not_ahead_of_actual(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.x_actual_pos = 10.0

    ok, _reason = sim.send_packet(
        target_x=10.0005, target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False
    )

    assert ok is False
    svc._worker.request_write_sequence.assert_not_called()


def test_send_packet_rejects_non_finite_target(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.x_actual_pos = 0.0

    ok1, _ = sim.send_packet(target_x=float("nan"), target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False)
    ok2, _ = sim.send_packet(target_x=float("inf"), target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False)

    assert ok1 is False
    assert ok2 is False
    svc._worker.request_write_sequence.assert_not_called()


def test_send_packet_rejects_confidence_out_of_bounds(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.x_actual_pos = 0.0

    ok, _reason = sim.send_packet(
        target_x=1.0, target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False, confidence=1.5
    )

    assert ok is False
    svc._worker.request_write_sequence.assert_not_called()


def test_send_packet_requires_armed(tmp_path):
    svc = _service(tmp_path)

    ok, _reason = sim_send_packet_unarmed(svc)

    assert ok is False
    svc._worker.request_write_sequence.assert_not_called()


def sim_send_packet_unarmed(svc: MachineService):
    sim = VisionSimulatorService(svc)
    return sim.send_packet(target_x=1.0, target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False)


def test_second_packet_rejected_while_first_in_flight(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.x_actual_pos = 0.0

    ok1, reason1 = sim.send_packet(target_x=1.0, target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False)
    ok2, reason2 = sim.send_packet(target_x=2.0, target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False)

    assert ok1 is True, reason1
    assert ok2 is False
    assert svc._worker.request_write_sequence.call_count == 1


# -- packet result handling: sequence advance, stale-generation guard -------


def test_packet_result_success_advances_sequence_and_clears_in_flight(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.x_actual_pos = 0.0
    sim.send_packet(target_x=1.0, target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False)
    results: list[tuple[bool, str]] = []
    sim.packetResult.connect(lambda ok, msg: results.append((ok, msg)))

    svc.visionSequentialWriteResult.emit(True, "")

    assert sim._send_in_flight is False
    assert sim._sequence_value == 1
    assert results == [(True, "")]


def test_packet_result_failure_does_not_advance_sequence(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.x_actual_pos = 0.0
    sim.send_packet(target_x=1.0, target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False)
    before = sim._sequence_value

    svc.visionSequentialWriteResult.emit(False, "Yazma başarısız: vision_target_y")

    assert sim._sequence_value == before
    assert sim._send_in_flight is False


def test_stale_packet_result_after_disarm_is_ignored(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.x_actual_pos = 0.0
    sim.send_packet(target_x=1.0, target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False)
    sim._force_disarm("test: reconnect arrived before the result")
    results: list[tuple[bool, str]] = []
    sim.packetResult.connect(lambda ok, msg: results.append((ok, msg)))

    svc.visionSequentialWriteResult.emit(True, "")

    assert results == []
    assert sim._sequence_value == 0


# -- UInt32 wraparound --------------------------------------------------------


def test_sequence_wraps_at_uint32(tmp_path):
    svc = _service(tmp_path)
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.stale = False
    svc.snapshot.vision_sequence = 2**32 - 1
    sim = VisionSimulatorService(svc)
    sim.arm()
    svc.snapshot.x_actual_pos = 0.0

    sim.send_packet(target_x=1.0, target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False)

    (fields,), _kwargs = svc._worker.request_write_sequence.call_args
    assert dict(fields)["vision_sequence"] == 0


def test_heartbeat_wraps_at_uint32(tmp_path):
    svc, sim = _armed(tmp_path)
    sim._heartbeat_value = 2**32 - 1

    sim._on_heartbeat_tick()

    svc._worker.request_write.assert_called_with("vision_heartbeat", 0)


# -- heartbeat lifecycle -------------------------------------------------------


def test_heartbeat_requires_armed(tmp_path):
    svc = _service(tmp_path)
    sim = VisionSimulatorService(svc)

    ok, _reason = sim.set_heartbeat_enabled(True)

    assert ok is False
    assert sim.heartbeat_active is False


def test_heartbeat_period_derived_from_settings_timeout_not_hardcoded(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.set_parameter("t_vision_heartbeat_timeout", 900.0)

    ok, reason = sim.set_heartbeat_enabled(True)

    assert ok, reason
    assert sim._heartbeat_timer.interval() == 300  # 900 / 3, not a hardcoded 2000ms
    sim.set_heartbeat_enabled(False)
    assert sim.heartbeat_active is False


def test_heartbeat_tick_stops_itself_if_disarmed_meanwhile(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.set_heartbeat_enabled(True)
    sim.disarm()

    sim._on_heartbeat_tick()

    assert sim.heartbeat_active is False


# -- explicit operator actions (cut permit / z down request) ----------------


def test_cut_permit_and_z_down_require_armed(tmp_path):
    svc = _service(tmp_path)
    sim = VisionSimulatorService(svc)

    ok1, _ = sim.send_cut_permit(True)
    ok2, _ = sim.send_z_down_request(True)

    assert ok1 is False
    assert ok2 is False
    svc._worker.request_write.assert_not_called()


def test_cut_permit_and_z_down_write_when_armed(tmp_path):
    svc, sim = _armed(tmp_path)

    sim.send_cut_permit(True)
    sim.send_z_down_request(True)

    svc._worker.request_write.assert_any_call("vision_cut_permit", True)
    svc._worker.request_write.assert_any_call("vision_z_down_request", True)


# -- disarm lifecycle ----------------------------------------------------------


def test_disarm_while_cycle_passive_retracts_permission_fields(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.cycle_active = False

    ok, note = sim.disarm()

    assert ok is True
    assert note == ""
    calls = [c.args for c in svc._worker.request_write.call_args_list]
    assert ("vision_ready", False) in calls
    assert ("vision_cut_permit", False) in calls
    assert ("vision_z_down_request", False) in calls
    assert sim.armed is False


def test_disarm_while_cycle_active_skips_retraction_and_warns(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.cycle_active = True
    svc._worker.reset_mock()

    ok, note = sim.disarm()

    assert ok is True
    assert note != ""
    svc._worker.request_write.assert_not_called()
    assert sim.armed is False


def test_disarm_when_already_disarmed_is_a_harmless_noop(tmp_path):
    svc = _service(tmp_path)
    sim = VisionSimulatorService(svc)

    ok, note = sim.disarm()

    assert ok is True
    assert note == ""


# -- demo mode: harmless, no real PLC involved -------------------------------


def test_demo_mode_arm_and_dispatch_is_harmless(tmp_path):
    svc, sim = _armed(tmp_path, demo=True)
    svc.snapshot.x_actual_pos = 0.0

    ok, reason = sim.send_packet(target_x=1.0, target_y=0.0, vision_ready=True, line_valid=True, vision_fault=False)

    assert ok, reason
