"""PLC-HMI-20260922-18 (HMI-A05, C06_1 audit): "MESAJ" sınıfı (M01-M09)
statik referans olarak var ama hiçbir yerde CANLI olarak üretilmiyordu.
`compute_active_state_message` yalnız state->mesaj eşlemesini (M01-M07/M09)
test eder - saf, Qt'siz. M08'in "yalnız yeni sonuç" (edge) davranışı
`test_machine_page_warning_table.py`'daki widget testleriyle kapsanır."""

from __future__ import annotations

from core.cycle_state import CycleState
from core.models import MachineSnapshot
from ui.machine.machine_page import compute_active_state_message


def _snap(**overrides) -> MachineSnapshot:
    snap = MachineSnapshot(stale=False)
    for key, value in overrides.items():
        setattr(snap, key, value)
    return snap


def test_no_message_when_stale():
    """Görev notu: "bağlantı eskiyse kesin proses mesajı üretme"."""
    snap = _snap(stale=True, cycle_state=int(CycleState.WAIT_VISION))

    assert compute_active_state_message(snap) is None


def test_no_message_for_a_state_with_no_mapping():
    snap = _snap(cycle_state=int(CycleState.MANUAL))

    assert compute_active_state_message(snap) is None


def test_wait_vision_is_m01():
    snap = _snap(cycle_state=int(CycleState.WAIT_VISION))
    assert compute_active_state_message(snap) == "[M01] Kamera verisi bekleniyor."


def test_wait_blade_request_is_m02():
    snap = _snap(cycle_state=int(CycleState.WAIT_BLADE_REQUEST))
    assert compute_active_state_message(snap) == "[M02] Bıçak talebi / geçerli yörünge bekleniyor."


def test_clamp_down_and_blade_down_both_map_to_m03():
    down_msg = "[M03] Baskı/bıçak aşağı sensörü bekleniyor."
    assert compute_active_state_message(_snap(cycle_state=int(CycleState.CLAMP_DOWN))) == down_msg
    assert compute_active_state_message(_snap(cycle_state=int(CycleState.BLADE_DOWN))) == down_msg


def test_blade_up_and_clamp_up_both_map_to_m04():
    up_msg = "[M04] Bıçak/baskı aşağı sensöründen çıkış bekleniyor."
    assert compute_active_state_message(_snap(cycle_state=int(CycleState.BLADE_UP))) == up_msg
    assert compute_active_state_message(_snap(cycle_state=int(CycleState.CLAMP_UP))) == up_msg


def test_manual_return_is_m05():
    snap = _snap(cycle_state=int(CycleState.MANUAL_RETURN))
    assert compute_active_state_message(snap) == "[M05] Başlangıç konumuna dönülüyor."


def test_manual_return_stop_is_m06():
    snap = _snap(cycle_state=int(CycleState.MANUAL_RETURN_STOP))
    assert compute_active_state_message(snap) == "[M06] Dönüş durduruluyor; talepleri bırakın."


def test_recovery_is_m07():
    snap = _snap(cycle_state=int(CycleState.RECOVERY))
    assert compute_active_state_message(snap) == "[M07] Manuel modu seçerek hazırlığı yapın."


def test_stopping_is_m09():
    snap = _snap(cycle_state=int(CycleState.STOPPING))
    assert (
        compute_active_state_message(snap)
        == "[M09] Otomatik çevrim durduruluyor; mevcut devam yolu bıçak yukarı/eksen dönüşü."
    )
