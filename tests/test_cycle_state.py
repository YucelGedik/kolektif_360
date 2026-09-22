from core.cycle_state import CycleState, cycle_state_label


def test_known_state_has_turkish_label():
    assert cycle_state_label(int(CycleState.CUTTING)) == "Kesim"


def test_unknown_state_degrades_gracefully():
    assert "Bilinmeyen" in cycle_state_label(9999)


def test_all_enum_members_have_labels():
    for state in CycleState:
        label = cycle_state_label(int(state))
        assert label and "Bilinmeyen" not in label


def test_manual_return_stop_label_is_in_progress_not_past_tense():
    """PLC-HMI-20260922-18 (HMI-A06, C06_1 audit): "Durduruldu" (tamamlanmış)
    yanlıştı - süreç henüz tamamlanmadı. PLC'nin kendi 13 numaralı bulgusu
    da "durduruluyor" (sürüyor) diyor."""
    label = cycle_state_label(int(CycleState.MANUAL_RETURN_STOP))
    assert label == "Başlangıca Dönüş Durduruluyor"
    assert "Durduruldu" not in label


def test_recovery_label_matches_plc_instructed_wording():
    """PLC-HMI-20260922-18 (HMI-A06): PLC'nin 2026-09-18 açık talimatı -
    "Eski otomatik dönüş/recovery ifadesi kullanılmamalı." - "Recovery"
    kelimesi kendisi hiç görünmemeli."""
    label = cycle_state_label(int(CycleState.RECOVERY))
    assert label == "Manuel Hazırlık Bekleniyor"
    assert "Recovery" not in label
