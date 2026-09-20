"""H3 (2026-09-18, kullanıcı test notu): StartPermitted=FALSE nedeninin
operatöre açık şekilde bildirilmesi. `compute_start_inhibit_reasons` PLC'nin
kendi xStartPermitted formülünü yeniden hesaplamaz - yalnız PLC'nin zaten
yayınladığı alt bileşenlerden (servo/vision/emergency, xX_AtStart/
xY_AtCenter, manual_mode, cycle_active) bir açıklama üretir. Gerçek bir
PLC'ye bağlanılmaz - saf `MachineSnapshot` girdisiyle test edilir."""

from __future__ import annotations

from core.models import MachineSnapshot
from ui.machine.machine_page import compute_start_inhibit_reasons


def _ready_snapshot(**overrides) -> MachineSnapshot:
    snap = MachineSnapshot(
        stale=False,
        start_permitted=False,
        manual_mode=False,
        cycle_active=False,
        emergency_active=False,
        x_servo_ready=True,
        y_servo_ready=True,
        vision_ready=True,
        vision_heartbeat_ok=True,
        vision_fault=False,
        x_at_start=True,
        y_at_center=True,
    )
    for key, value in overrides.items():
        setattr(snap, key, value)
    return snap


def test_no_reasons_when_start_is_permitted():
    snap = _ready_snapshot(start_permitted=True)

    assert compute_start_inhibit_reasons(snap, 0.0, 0.0) == []


def test_no_reasons_when_stale():
    snap = _ready_snapshot(stale=True)

    assert compute_start_inhibit_reasons(snap, 0.0, 0.0) == []


def test_manual_mode_reason_is_exclusive():
    snap = _ready_snapshot(manual_mode=True, x_at_start=False, y_at_center=False)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert reasons == ["Manuel modda — Start otomatik modda kullanılır."]


def test_cycle_active_reason_is_exclusive():
    snap = _ready_snapshot(cycle_active=True, x_at_start=False)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert reasons == ["Çevrim zaten aktif."]


def test_x_only_reason_shows_configured_start_pos():
    snap = _ready_snapshot(x_at_start=False)

    reasons = compute_start_inhibit_reasons(snap, 12.5, 0.0)

    assert reasons == ["X başlangıç konumunda değil (ayarlı: 12.5 mm)."]


def test_y_only_reason_shows_configured_center_pos():
    snap = _ready_snapshot(y_at_center=False)

    reasons = compute_start_inhibit_reasons(snap, 0.0, -3.0)

    assert reasons == ["Y merkez konumunda değil (ayarlı: -3 mm)."]


def test_both_axes_reasons_shown_together():
    snap = _ready_snapshot(x_at_start=False, y_at_center=False)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert len(reasons) == 2
    assert any("X başlangıç" in r for r in reasons)
    assert any("Y merkez" in r for r in reasons)


def test_vision_missing_reason():
    snap = _ready_snapshot(vision_heartbeat_ok=False)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert reasons == ["Vision hazır değil."]


def test_vision_fault_also_counts_as_not_ready():
    snap = _ready_snapshot(vision_fault=True)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert reasons == ["Vision hazır değil."]


def test_emergency_and_servo_reasons():
    snap = _ready_snapshot(emergency_active=True, x_servo_ready=False)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert "Acil durdurma aktif." in reasons
    assert "X servo hazır değil." in reasons


def test_fallback_reason_when_nothing_known_explains_it():
    """MachineReady/StartPermitted FALSE olabilir ama HMI'nin gördüğü tüm
    alt bileşenler TRUE - bilinmeyen bir PLC koşulu var, kesin bir neden
    icat edilmez, dürüst bir "bilinmiyor" mesajı gösterilir."""
    snap = _ready_snapshot()  # her şey "hazır" ama start_permitted False

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert len(reasons) == 1
    assert "bilinen koşulların dışında" in reasons[0]


def test_stop_pressed_is_never_fabricated_as_a_reason():
    """Görev notu: bulunmayan tag için bool tahmini yapılmaz - fiziksel
    Stop'un "şu an basılı" durumu için gerçek bir PLC tagı yok, dolayısıyla
    hiçbir koşulda "Stop basılı" metni üretilmemeli."""
    snap = _ready_snapshot(x_at_start=False, y_at_center=False, emergency_active=True)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert not any("stop" in r.lower() for r in reasons)
