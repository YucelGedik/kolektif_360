"""H6 (2026-09-18, PLC-HMI-20260918-04): kontrollü eğimli otomatik kamera
senaryosu. Varsayılan düz çizgi modu değişmez; "tilted" ikinci, açıkça
seçilen bir senaryodur: TargetY = y0 + m*(TargetX - x0), sabit bir çevrim-
başlangıç referansından. Gerçek bir PLC'ye bağlanılmaz - mock worker."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.cycle_state import CycleState
from core.models import ConnectionState
from services.machine_service import MachineService
from services.vision_simulator import VisionSimulatorService


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
    svc.snapshot.lr_max_allowed_slope = 0.02
    sim = VisionSimulatorService(svc)
    ok, reason = sim.arm()
    assert ok, reason
    return svc, sim


def _sequence_field_dict(svc: MachineService, call_index: int = -1) -> dict:
    (fields,), _ = svc._worker.request_write_sequence.call_args_list[call_index]
    return dict(fields)


def test_default_scenario_is_straight(tmp_path):
    svc, sim = _armed(tmp_path)

    assert sim.camera_scenario == "straight"


def test_scenario_cannot_change_while_auto_camera_active(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.start_auto_camera()

    ok, reason = sim.set_camera_scenario("tilted", 0.01)

    assert ok is False
    assert sim.camera_scenario == "straight"


def _configure_generous_bounds(svc: MachineService) -> None:
    # Test'i olası önceki oturumlardan kalan persisted Settings override'
    # larından (SettingsStore paylaşımlı bir DB kullanıyor) bağımsız kılmak
    # için, gerekli tüm parametreleri açıkça, birbiriyle tutarlı şekilde ayarla.
    svc.set_parameter("lr_x_cut_end_pos", 300.0)
    svc.set_parameter("lr_y_software_min", -30.0)
    svc.set_parameter("lr_y_software_max", 30.0)
    svc.set_parameter("lr_x_cut_velocity", 50.0)
    svc.set_parameter("lr_y_max_velocity", 5.0)


def test_positive_small_slope_is_accepted_and_used(tmp_path):
    svc, sim = _armed(tmp_path)
    _configure_generous_bounds(svc)
    svc.snapshot.x_actual_pos = 0.0
    svc.snapshot.y_actual_pos = 0.0

    ok, reason = sim.set_camera_scenario("tilted", 0.01)
    assert ok, reason
    ok, reason = sim.start_auto_camera()
    assert ok, reason

    svc.snapshot.cycle_state = int(CycleState.WAIT_VISION)
    sim._on_auto_camera_tick()

    fields = _sequence_field_dict(svc)
    target_x = fields["vision_target_x"]
    target_y = fields["vision_target_y"]
    assert target_y == 0.01 * (target_x - 0.0) + 0.0


def test_negative_small_slope_is_accepted_and_used(tmp_path):
    svc, sim = _armed(tmp_path)
    _configure_generous_bounds(svc)
    svc.snapshot.x_actual_pos = 0.0
    svc.snapshot.y_actual_pos = 0.0

    ok, reason = sim.set_camera_scenario("tilted", -0.01)
    assert ok, reason
    sim.start_auto_camera()
    svc.snapshot.cycle_state = int(CycleState.WAIT_VISION)
    sim._on_auto_camera_tick()

    fields = _sequence_field_dict(svc)
    assert fields["vision_target_y"] == -0.01 * (fields["vision_target_x"] - 0.0)


def test_zero_slope_behaves_like_a_flat_reference(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.x_actual_pos = 10.0
    svc.snapshot.y_actual_pos = 2.0  # non-zero reference Y

    sim.set_camera_scenario("tilted", 0.0)
    sim.start_auto_camera()
    svc.snapshot.cycle_state = int(CycleState.WAIT_VISION)
    sim._on_auto_camera_tick()

    fields = _sequence_field_dict(svc)
    assert fields["vision_target_y"] == 2.0  # y0, sabit kalır (m=0)


def test_slope_exceeding_max_allowed_slope_is_rejected(tmp_path):
    svc, sim = _armed(tmp_path)  # lr_max_allowed_slope = 0.02

    ok, reason = sim.set_camera_scenario("tilted", 0.05)

    assert ok is False
    assert "lrMaxAllowedSlope" in reason
    assert sim.camera_scenario == "straight"


def test_slope_exceeding_y_max_velocity_is_rejected(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.lr_max_allowed_slope = 1.0  # slope limiti gevşet, hız limiti sınasın
    svc.set_parameter("lr_x_cut_velocity", 175.0)
    svc.set_parameter("lr_y_max_velocity", 5.0)
    # required Y velocity = |slope| * 175 must stay <= 5.0 -> slope <= ~0.0286
    slope = 0.5  # 0.5 * 175 = 87.5 mm/s >> 5.0

    ok, reason = sim.set_camera_scenario("tilted", slope)

    assert ok is False
    assert "lrY_MaxVelocity" in reason


def test_slope_that_exceeds_software_bounds_at_cut_end_is_rejected(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.lr_max_allowed_slope = 1.0
    svc.snapshot.x_actual_pos = 0.0
    svc.snapshot.y_actual_pos = 0.0
    svc.set_parameter("lr_x_cut_end_pos", 3600.0)
    svc.set_parameter("lr_y_software_min", -30.0)
    svc.set_parameter("lr_y_software_max", 30.0)
    # At cut end (x=3600), y = 0 + slope*3600 must stay within [-30, 30]
    # -> |slope| must stay <= 30/3600 ~= 0.00833
    slope = 0.01  # 0.01*3600 = 36 > 30 -> reject

    ok, reason = sim.set_camera_scenario("tilted", slope)

    assert ok is False
    assert "sınırlarının" in reason


def test_reasonable_slope_within_all_limits_is_accepted(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.x_actual_pos = 0.0
    svc.snapshot.y_actual_pos = 0.0
    svc.set_parameter("lr_x_cut_end_pos", 3600.0)
    svc.set_parameter("lr_y_software_min", -30.0)
    svc.set_parameter("lr_y_software_max", 30.0)
    svc.set_parameter("lr_x_cut_velocity", 50.0)
    svc.set_parameter("lr_y_max_velocity", 5.0)
    # slope small enough for lrMaxAllowedSlope(0.02), Y velocity (5/50=0.1
    # headroom) and cut-end bounds (30/3600=0.0083 headroom)
    slope = 0.005

    ok, reason = sim.set_camera_scenario("tilted", slope)

    assert ok is True, reason


def test_out_of_bounds_target_y_is_rejected_per_packet_even_mid_travel(tmp_path):
    """"sınır dışı yolun reddi" - referans kabul edilse bile, ileri bakış
    hedefinin ANLIK olarak sınır dışına çıktığı bir tick reddedilmeli
    (send_packet'in Y bounds kontrolü, senaryo bağımsız)."""
    svc, sim = _armed(tmp_path)
    svc.snapshot.x_actual_pos = 0.0
    svc.snapshot.y_actual_pos = 0.0
    svc.set_parameter("lr_y_software_min", -30.0)
    svc.set_parameter("lr_y_software_max", 30.0)
    sim.set_camera_scenario("tilted", 0.008)  # kabul edilebilir referans eğimi
    sim.start_auto_camera()

    # actual X çok ileri gitti (örn. sensör/valfteki bir sapma) - lead ile
    # birlikte hedef Y artık sınırın çok dışında olacak.
    svc.snapshot.x_actual_pos = 5000.0
    svc.snapshot.cycle_state = int(CycleState.CUTTING)
    sim._on_auto_camera_tick()

    svc._worker.request_write_sequence.assert_not_called()


def test_forward_target_at_the_final_point_is_reasonable(tmp_path):
    """Kabul: "son noktadaki ileri hedef" - kesim sonuna yakın actual X'te
    bile hedefX-actualX>0 kalır (kırpma yapılmadığı için)."""
    svc, sim = _armed(tmp_path)
    svc.set_parameter("lr_x_cut_end_pos", 300.0)
    svc.snapshot.x_actual_pos = 299.0  # cut end'e çok yakın
    svc.snapshot.y_actual_pos = 0.0
    sim.set_camera_scenario("tilted", 0.001)
    sim.start_auto_camera()
    svc.snapshot.cycle_state = int(CycleState.CUTTING)

    sim._on_auto_camera_tick()

    fields = _sequence_field_dict(svc)
    assert fields["vision_target_x"] > 299.0


def test_reference_point_is_captured_once_and_does_not_jump_mid_cycle(tmp_path):
    svc, sim = _armed(tmp_path)
    svc.snapshot.x_actual_pos = 10.0
    svc.snapshot.y_actual_pos = 1.0
    sim.set_camera_scenario("tilted", 0.01)
    sim.start_auto_camera()

    assert sim._tilt_reference == (10.0, 1.0)

    # Actual X/Y ilerledi ama referans SABİT kalmalı (y0,x0 sıçramaz).
    svc.snapshot.x_actual_pos = 50.0
    svc.snapshot.y_actual_pos = 5.0
    svc.snapshot.cycle_state = int(CycleState.CUTTING)
    sim._on_auto_camera_tick()

    assert sim._tilt_reference == (10.0, 1.0)


def test_disarm_clears_tilt_reference_and_resets_on_next_arm(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.set_camera_scenario("tilted", 0.01)
    sim.start_auto_camera()
    assert sim._tilt_reference is not None

    sim.disarm()

    assert sim._tilt_reference is None
    assert sim.auto_camera_active is False


def test_reconnect_cancels_auto_camera_and_tilt_reference(tmp_path):
    svc, sim = _armed(tmp_path)
    sim.set_camera_scenario("tilted", 0.01)
    sim.start_auto_camera()

    svc.connectionStateChanged.emit(ConnectionState.ERROR)

    assert sim._tilt_reference is None
    assert sim.auto_camera_active is False
    assert sim.armed is False


def test_straight_scenario_unaffected_by_tilt_machinery(tmp_path):
    """Varsayılan düz çizgi modu davranışı değişmedi - TargetY hep canlı
    lrY_CenterPosition, referans mekanizmasından etkilenmez."""
    svc, sim = _armed(tmp_path)
    svc.set_parameter("lr_y_center_position", 3.0)
    svc.snapshot.x_actual_pos = 0.0

    sim.start_auto_camera()  # scenario hâlâ "straight"
    svc.snapshot.cycle_state = int(CycleState.WAIT_VISION)
    sim._on_auto_camera_tick()

    fields = _sequence_field_dict(svc)
    assert fields["vision_target_y"] == 3.0
