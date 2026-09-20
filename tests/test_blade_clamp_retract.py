"""PLC-HMI-20260918-06: manuel Bıçak/Baskı Yukarı (Geri Çek) requestleri.
GVL.xBladeRetractRequest / GVL.xClampRetractRequest pulse ile yazılır;
GVL.xBladeRetractAccepted / GVL.xClampRetractAccepted PLC-üretimli, salt
okunur kabul bitleridir - HMI hiçbir zaman yazmaz. Manuel "Aşağı" için PLC'de
henüz bir request tanımlı değil (ayrı, açık görev) - bu modülde test edilen
davranış yok, çünkü HMI tarafında da işlevli bir buton yok. Gerçek bir PLC'ye
bağlanılmaz - gerçek mod bir MagicMock worker ile taklit edilir."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.machine_service import MachineService


def _demo_service(tmp_path) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text('{"endpoint": "", "nodes": {}}', encoding="utf-8")
    return MachineService(config_path=cfg)


def _real_service(tmp_path) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(
        '{"endpoint": "opc.tcp://192.168.0.2:4840", "nodes": {}}', encoding="utf-8"
    )
    svc = MachineService(config_path=cfg)
    svc._worker = MagicMock()
    return svc


# -- MachineService: real mode -----------------------------------------------


def test_request_blade_retract_pulses_the_real_tag_when_manual_allowed(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.manual_mode = True
    svc.snapshot.cycle_state = 10  # CycleState.MANUAL

    svc.request_blade_retract()

    svc._worker.request_pulse.assert_called_once_with("cmd_blade_retract")


def test_request_clamp_retract_pulses_the_real_tag_when_manual_allowed(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.manual_mode = True
    svc.snapshot.cycle_state = 10

    svc.request_clamp_retract()

    svc._worker.request_pulse.assert_called_once_with("cmd_clamp_retract")


def test_retract_requests_refused_outside_manual_mode(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.manual_mode = False

    svc.request_blade_retract()
    svc.request_clamp_retract()

    svc._worker.request_pulse.assert_not_called()


def test_retract_requests_refused_during_an_active_auto_cycle_state(tmp_path):
    svc = _real_service(tmp_path)
    svc.snapshot.manual_mode = True
    svc.snapshot.cycle_state = 80  # CycleState.CUTTING, an AUTO_CYCLE_ACTIVE_STATE

    svc.request_blade_retract()
    svc.request_clamp_retract()

    svc._worker.request_pulse.assert_not_called()


# -- MachineService: raw snapshot parsing ------------------------------------


def test_accepted_bits_are_read_directly_not_derived(tmp_path):
    svc = _demo_service(tmp_path)

    svc._on_raw_snapshot({"blade_retract_accepted": True, "clamp_retract_accepted": False})
    assert svc.snapshot.blade_retract_accepted is True
    assert svc.snapshot.clamp_retract_accepted is False

    svc._on_raw_snapshot({"blade_retract_accepted": False, "clamp_retract_accepted": True})
    assert svc.snapshot.blade_retract_accepted is False
    assert svc.snapshot.clamp_retract_accepted is True


# -- MachineService: demo mode ------------------------------------------------


def test_demo_mode_retract_requests_delegate_to_demo_simulator(tmp_path):
    svc = _demo_service(tmp_path)
    svc.snapshot.manual_mode = True
    svc.snapshot.cycle_state = 10

    svc.request_blade_retract()
    svc.request_clamp_retract()

    assert svc._demo.blade_retract_requested is True
    assert svc._demo.clamp_retract_requested is True


# -- DemoSimulator: end-to-end tick behavior ----------------------------------


def test_demo_blade_retract_sets_up_and_accepted_after_a_tick(tmp_path):
    svc = _demo_service(tmp_path)
    svc.snapshot.manual_mode = True
    svc._demo.manual_mode = True
    svc.snapshot.blade_down = True
    svc.snapshot.blade_up = False

    svc.request_blade_retract()
    svc._on_tick()

    assert svc.snapshot.blade_down is False
    assert svc.snapshot.blade_up is True
    assert svc.snapshot.blade_retract_accepted is True
    assert svc._demo.blade_retract_requested is False  # tek seferlik, tekrar tetiklenmez


def test_demo_clamp_retract_sets_up_and_accepted_after_a_tick(tmp_path):
    svc = _demo_service(tmp_path)
    svc.snapshot.manual_mode = True
    svc._demo.manual_mode = True
    svc.snapshot.clamp_down = True
    svc.snapshot.clamp_up = False

    svc.request_clamp_retract()
    svc._on_tick()

    assert svc.snapshot.clamp_down is False
    assert svc.snapshot.clamp_up is True
    assert svc.snapshot.clamp_retract_accepted is True


def test_demo_blade_and_clamp_retract_are_independent(tmp_path):
    """Iki talep bağımsız, istenen sırada veya birlikte (görev notu)."""
    svc = _demo_service(tmp_path)
    svc.snapshot.manual_mode = True
    svc._demo.manual_mode = True
    svc.snapshot.blade_down = True
    svc.snapshot.clamp_down = True

    svc.request_clamp_retract()
    svc._on_tick()

    assert svc.snapshot.clamp_retract_accepted is True
    assert svc.snapshot.blade_retract_accepted is False  # sadece istenen taraf
    assert svc.snapshot.blade_down is True  # dokunulmadı


def test_demo_new_fault_resets_accepted_bits(tmp_path):
    """Gerçek PLC her yeni FAULT'ta kabul bitlerini sıfırlar (görev notu) -
    demo simülatörü aynı davranışı taklit eder."""
    svc = _demo_service(tmp_path)
    svc.snapshot.manual_mode = True
    svc._demo.manual_mode = True
    svc.request_blade_retract()
    svc._on_tick()
    assert svc.snapshot.blade_retract_accepted is True

    svc._demo._raise_demo_alarm(svc.snapshot, svc._alarms, lambda: None)

    assert svc.snapshot.blade_retract_accepted is False
    assert svc.snapshot.clamp_retract_accepted is False
