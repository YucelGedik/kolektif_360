"""H3 (2026-09-18) + C6/U-katalog (PLC-HMI-20260921-15/16, 2026-09-21):
StartPermitted=FALSE nedeninin operatöre açık şekilde, TÜMÜYLE (yalnız
ilk/tek neden değil) bildirilmesi. `compute_start_inhibit_reasons` PLC'nin
kendi xStartPermitted formülünü yeniden hesaplamaz - yalnız PLC'nin zaten
yayınladığı alt bileşenlerden bir açıklama listesi üretir. Gerçek bir PLC'ye
bağlanılmaz - saf `MachineSnapshot` girdisiyle test edilir."""

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
        x_fault=False,
        y_fault=False,
        vision_ready=True,
        vision_heartbeat_ok=True,
        vision_fault=False,
        x_at_start=True,
        y_at_center=True,
        blade_down=False,
        clamp_down=False,
        blade_retract_accepted=True,
        clamp_retract_accepted=True,
        manual_preparation_required=False,
        operator_stop_active=False,
    )
    for key, value in overrides.items():
        setattr(snap, key, value)
    return snap


def test_no_reasons_when_start_is_permitted():
    snap = _ready_snapshot(start_permitted=True)

    assert compute_start_inhibit_reasons(snap, 0.0, 0.0) == []


def test_stale_shows_its_own_warning_instead_of_hiding():
    """U10 (2026-09-21 değişikliği): eskiden stale iken liste tamamen boştu
    (hiçbir şey gösterilmiyordu) - artık veri eksikliği açıkça belirtiliyor,
    izin/konum nedeni UYDURULMUYOR."""
    snap = _ready_snapshot(stale=True)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert reasons == ["PLC verisi güncel değil; izin/konum bilgisi doğrulanamıyor."]


def test_cycle_active_shows_no_warning_normal_state():
    """Görev notu: aktif çevrimde Start uygun değil bilgisi normal bir
    durumdur, alarm yağmuruna çevrilmez - hiçbir UYARI üretilmez."""
    snap = _ready_snapshot(cycle_active=True, x_at_start=False)

    assert compute_start_inhibit_reasons(snap, 0.0, 0.0) == []


def test_manual_mode_combines_with_other_reasons_not_exclusive():
    """PLC-HMI-20260921-15: "ilk engelde return edip diğerlerini gizleme" -
    manuel modda VE eksenler konumunda değilken hepsi birlikte listelenir."""
    snap = _ready_snapshot(manual_mode=True, x_at_start=False, y_at_center=False)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert "Start için Otomatik modu seçin." in reasons
    assert any("X başlangıç" in r for r in reasons)
    assert any("Y merkez" in r for r in reasons)


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


def test_vision_heartbeat_missing_reason():
    snap = _ready_snapshot(vision_heartbeat_ok=False)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert reasons == ["Vision heartbeat alınmıyor/güncellenmiyor. PLC bağlantısı taze olmalı."]


def test_vision_not_ready_reason():
    snap = _ready_snapshot(vision_ready=False)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert reasons == ["Vision hazır değil."]


def test_vision_fault_is_not_duplicated_as_a_warning():
    """VisionFault gerçek bir HATA'dır (H17, `_update_alarm_conditions`) -
    burada ayrıca "Vision hazır değil" UYARISI olarak TEKRAR gösterilmez."""
    snap = _ready_snapshot(vision_fault=True, vision_ready=False)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert not any("Vision" in r for r in reasons)


def test_servo_not_ready_without_known_fault_is_a_warning():
    snap = _ready_snapshot(x_servo_ready=False)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert reasons == ["X servo hazır değil."]


def test_servo_fault_is_not_duplicated_as_a_warning():
    """x_fault (H06, gerçek HATA) varken servo_ready zaten False olur ama
    burada AYRICA "servo hazır değil" UYARISI olarak tekrar gösterilmez -
    HATA panosu zaten gösteriyor."""
    snap = _ready_snapshot(x_servo_ready=False, x_fault=True)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert not any("servo" in r.lower() for r in reasons)


def test_blade_down_blocks_start_clamp_does_not():
    """U05: yalnız bıçak - baskı için Start öncesi aşağı/yukarı koşulu
    görev notuyla açıkça EKLENMEDİ."""
    snap = _ready_snapshot(blade_down=True, clamp_down=True)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert reasons == ["Start için bıçağı kaldırın."]


def test_operator_stop_active_reason():
    """U06 - PLC henüz bu tag'i build/export etmedi (aday), ama kod hazır;
    tag config'e eklenince otomatik aktive olur."""
    snap = _ready_snapshot(operator_stop_active=True)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert reasons == ["Stop talebi aktif; Start engelli."]


def test_manual_preparation_required_lists_concrete_missing_conditions():
    """U04: jenerik "hazırlık gerekiyor" değil - PLC'nin xManualPreparation
    Required'ı FALSE'a çekme formülünden türetilmiş somut eksik listesi."""
    snap = _ready_snapshot(
        manual_preparation_required=True,
        blade_retract_accepted=False,
        clamp_down=True,
    )

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert len(reasons) == 1
    assert "bıçak Yukarı kabulü bekleniyor" in reasons[0]
    assert "baskı hâlâ aşağıda" in reasons[0]


def test_manual_preparation_required_with_nothing_missing_is_generic():
    snap = _ready_snapshot(manual_preparation_required=True)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert reasons == ["Manuel hazırlığı tamamlayın."]


def test_emergency_active_is_not_duplicated_as_a_warning():
    """Emniyet (H16) artık bir HATA - burada UYARI olarak gösterilmez."""
    snap = _ready_snapshot(emergency_active=True)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert not any("cil" in r for r in reasons)  # "Acil durdurma" yok


def test_fallback_reason_when_nothing_known_explains_it():
    """MachineReady/StartPermitted FALSE olabilir ama HMI'nin gördüğü tüm
    alt bileşenler TRUE - bilinmeyen bir PLC koşulu var, kesin bir neden
    icat edilmez, dürüst bir "bilinmiyor" mesajı gösterilir (U11)."""
    snap = _ready_snapshot()  # her şey "hazır" ama start_permitted False

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert reasons == ["PLC Start izni yok; ek koşul bilgisi gerekli."]


def test_stop_pressed_is_never_fabricated_as_a_reason():
    """Görev notu: bulunmayan tag için bool tahmini yapılmaz - fiziksel
    Stop'un "şu an basılı" durumu için gerçek bir PLC tagı yok (xOperator
    StopActive PLC'de henüz build/export edilmedi, hep False), dolayısıyla
    hiçbir koşulda "Stop basılı" metni üretilmemeli."""
    snap = _ready_snapshot(x_at_start=False, y_at_center=False)

    reasons = compute_start_inhibit_reasons(snap, 0.0, 0.0)

    assert not any("stop" in r.lower() for r in reasons)
