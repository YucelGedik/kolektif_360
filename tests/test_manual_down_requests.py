"""PLC-HMI-20260921-09: manuel bıçak/baskı Aşağı talepleri
(GVL.xBladeDownRequest / GVL.xClampDownRequest, ikisi de YENİ) + var olan
Yukarı (Geri Çek) taleplerinin artık paylaştığı, daha eksiksiz "ortak izin"
kontrolü. PLC ST teslimi hazır ama kullanıcı henüz build/export/online test
yapmadı - bu testler yalnız HMI mantığını izole doğrular, gerçek bir PLC'ye
bağlanılmaz (gerçek mod bir MagicMock worker ile taklit edilir)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

from core.models import ConnectionState
from services.machine_service import MachineService

MANUAL = 10  # CycleState.MANUAL
CUTTING = 80  # CycleState.CUTTING, an AUTO_CYCLE_ACTIVE_STATE


def _real_service(tmp_path, pulse_ms: int = 10) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(
        f'{{"endpoint": "opc.tcp://192.168.0.2:4840", "command_pulse_ms": {pulse_ms}, "nodes": {{}}}}',
        encoding="utf-8",
    )
    svc = MachineService(config_path=cfg)
    svc._worker = MagicMock()
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.stale = False
    svc.snapshot.manual_mode = True
    svc.snapshot.cycle_state = MANUAL
    return svc


def _demo_service(tmp_path) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text('{"endpoint": "", "nodes": {}}', encoding="utf-8")
    svc = MachineService(config_path=cfg)
    svc.snapshot.stale = False
    svc.snapshot.manual_mode = True
    svc.snapshot.cycle_state = MANUAL
    svc._demo.manual_mode = True
    return svc


# -- common permission (shared by all four buttons) -------------------------


def test_common_permission_allowed_by_default_in_manual(tmp_path):
    svc = _real_service(tmp_path)
    assert svc.manual_pneumatic_allowed() is True
    assert svc.manual_blade_down_allowed() is True
    assert svc.manual_clamp_down_allowed() is True


def test_common_permission_refused_outside_manual_cycle_state(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.cycle_state = CUTTING
    assert svc.manual_pneumatic_allowed() is False


def test_common_permission_refused_when_not_manual_mode(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.manual_mode = False
    assert svc.manual_pneumatic_allowed() is False


def test_common_permission_refused_when_stale(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.stale = True
    assert svc.manual_pneumatic_allowed() is False


def test_common_permission_refused_when_disconnected(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.connection_state = ConnectionState.DISCONNECTED
    assert svc.manual_pneumatic_allowed() is False


def test_common_permission_refused_when_emergency_not_ok(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.emergency_ok = False
    assert svc.manual_pneumatic_allowed() is False


def test_common_permission_refused_on_alarm_stop_request(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.alarm_stop_request = True
    assert svc.manual_pneumatic_allowed() is False


def test_common_permission_refused_on_motion_stop(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.motion_stop = True
    assert svc.manual_pneumatic_allowed() is False


def test_common_permission_refused_while_x_axis_moving(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.x_actual_vel = 5.0
    assert svc.manual_pneumatic_allowed() is False


def test_common_permission_refused_while_y_axis_moving(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.y_actual_vel = -5.0
    assert svc.manual_pneumatic_allowed() is False


def test_common_permission_refused_while_jog_active(tmp_path):
    svc = _real_service(tmp_path)
    svc.jog_x(1, True)
    assert svc.manual_pneumatic_allowed() is False
    svc.jog_x(1, False)
    assert svc.manual_pneumatic_allowed() is True


def test_release_all_jog_clears_jog_active_lock(tmp_path):
    svc = _real_service(tmp_path)
    svc.jog_y(-1, True)
    assert svc.manual_pneumatic_allowed() is False
    svc.release_all_jog()
    assert svc.manual_pneumatic_allowed() is True


# -- Down-only extra conditions ----------------------------------------------


def test_down_refused_during_manual_preparation_but_up_still_allowed(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.manual_preparation_required = True
    assert svc.manual_pneumatic_allowed() is True  # Yukarı serbest kalmalı
    assert svc.manual_blade_down_allowed() is False
    assert svc.manual_clamp_down_allowed() is False


def test_down_refused_while_feed_forward_pushbutton_held(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.feed_forward_input = True
    assert svc.manual_blade_down_allowed() is False
    assert svc.manual_pneumatic_allowed() is True


def test_down_refused_while_feed_reverse_pushbutton_held(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.feed_reverse_input = True
    assert svc.manual_clamp_down_allowed() is False


def test_down_refused_while_feed_running(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.feed_running = True
    assert svc.manual_blade_down_allowed() is False


# -- MachineService: real mode pulse dispatch --------------------------------


def test_request_blade_down_pulses_the_new_tag_when_allowed(tmp_path):
    svc = _real_service(tmp_path)
    svc.request_blade_down()
    svc._worker.request_pulse.assert_called_once_with("cmd_blade_down")


def test_request_clamp_down_pulses_the_new_tag_when_allowed(tmp_path):
    svc = _real_service(tmp_path)
    svc.request_clamp_down()
    svc._worker.request_pulse.assert_called_once_with("cmd_clamp_down")


def test_request_blade_down_refused_outside_manual(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.cycle_state = CUTTING
    svc.request_blade_down()
    svc._worker.request_pulse.assert_not_called()


def test_retract_up_priority_blocks_a_same_mechanism_down_during_its_pulse_window(tmp_path):
    svc = _real_service(tmp_path, pulse_ms=200)
    svc.request_blade_retract()
    svc._worker.request_pulse.assert_called_once_with("cmd_blade_retract")

    svc.request_blade_down()  # still inside the 200ms retract pulse window
    svc._worker.request_pulse.assert_called_once_with("cmd_blade_retract")  # still just the one call


def test_down_allowed_again_once_the_retract_pulse_window_has_passed(tmp_path):
    svc = _real_service(tmp_path, pulse_ms=10)
    svc.request_blade_retract()
    time.sleep(0.02)

    svc.request_blade_down()

    assert svc._worker.request_pulse.call_args_list[-1].args == ("cmd_blade_down",)


def test_clamp_mechanism_independent_of_blade_pulse_window(tmp_path):
    svc = _real_service(tmp_path, pulse_ms=200)
    svc.request_blade_retract()

    svc.request_clamp_down()  # different mechanism, must not be blocked

    svc._worker.request_pulse.assert_any_call("cmd_clamp_down")


# -- demo mode ----------------------------------------------------------------


def test_demo_mode_down_requests_delegate_to_demo_simulator(tmp_path):
    svc = _demo_service(tmp_path)

    svc.request_blade_down()
    svc.request_clamp_down()

    assert svc._demo.blade_down_requested is True
    assert svc._demo.clamp_down_requested is True


def test_demo_blade_down_sets_down_and_clears_retract_accepted_after_a_tick(tmp_path):
    svc = _demo_service(tmp_path)
    svc.snapshot.blade_down = False
    svc.snapshot.blade_up = True
    svc.snapshot.blade_retract_accepted = True  # left over from a previous Up

    svc.request_blade_down()
    svc._on_tick()

    assert svc.snapshot.blade_down is True
    assert svc.snapshot.blade_up is False
    assert svc.snapshot.blade_retract_accepted is False


def test_demo_clamp_down_sets_down_after_a_tick(tmp_path):
    svc = _demo_service(tmp_path)
    svc.snapshot.clamp_down = False
    svc.snapshot.clamp_up = True

    svc.request_clamp_down()
    svc._on_tick()

    assert svc.snapshot.clamp_down is True
    assert svc.snapshot.clamp_up is False


def test_demo_retract_wins_over_down_when_both_requested_same_tick(tmp_path):
    svc = _demo_service(tmp_path)
    svc.snapshot.blade_down = True
    svc.snapshot.blade_up = False

    svc._demo.request_blade_retract()
    svc._demo.request_blade_down()
    svc._on_tick()

    assert svc.snapshot.blade_down is False
    assert svc.snapshot.blade_up is True
    assert svc.snapshot.blade_retract_accepted is True
    assert svc._demo.blade_down_requested is False  # discarded, not queued
