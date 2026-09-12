"""Single source of truth for PLC CycleState codes and their Turkish labels.

Numeric codes come from the integration brief (section 14) and are provisional
until the PLC state machine is finalized (brief section 28). UI code must never
display a raw integer; it must always go through `cycle_state_label`.
"""

from __future__ import annotations

from enum import IntEnum


class CycleState(IntEnum):
    INIT = 0
    IDLE = 10
    MANUAL_READY = 20
    WAIT_FOR_MATERIAL = 30
    AUTO_START_CHECK = 40
    CLAMP_DOWN = 50
    WAIT_VISION_LINE = 60
    BLADE_DOWN = 70
    CUTTING = 80
    CUT_FINISH = 90
    BLADE_UP = 100
    RETURN_X_Y = 110
    CLAMP_UP = 120
    CYCLE_COMPLETE = 130

    CONTROLLED_STOP = 500
    CUT_INTERRUPTED = 510
    RECOVERY = 520
    RECOVERY_BLADE_UP = 530
    RECOVERY_RETURN_X = 540
    RECOVERY_CENTER_Y = 550
    RECOVERY_CLAMP_UP = 560

    FAULT = 900


CYCLE_STATE_LABELS_TR: dict[CycleState, str] = {
    CycleState.INIT: "Başlatılıyor",
    CycleState.IDLE: "Bekliyor",
    CycleState.MANUAL_READY: "Manuel Hazır",
    CycleState.WAIT_FOR_MATERIAL: "Perde Bekleniyor",
    CycleState.AUTO_START_CHECK: "Start Kontrolü",
    CycleState.CLAMP_DOWN: "Perde Baskısı İniyor",
    CycleState.WAIT_VISION_LINE: "Kamera Çizgi Bekleniyor",
    CycleState.BLADE_DOWN: "Bıçak İniyor",
    CycleState.CUTTING: "Kesim",
    CycleState.CUT_FINISH: "Kesim Tamamlanıyor",
    CycleState.BLADE_UP: "Bıçak Kalkıyor",
    CycleState.RETURN_X_Y: "Eksenler Dönüyor",
    CycleState.CLAMP_UP: "Baskı Kalkıyor",
    CycleState.CYCLE_COMPLETE: "Çevrim Tamam",
    CycleState.CONTROLLED_STOP: "Kontrollü Duruş",
    CycleState.CUT_INTERRUPTED: "Kesim Yarıda Kaldı",
    CycleState.RECOVERY: "Toparlanma",
    CycleState.RECOVERY_BLADE_UP: "Toparlanma: Bıçak Kalkıyor",
    CycleState.RECOVERY_RETURN_X: "Toparlanma: X Dönüyor",
    CycleState.RECOVERY_CENTER_Y: "Toparlanma: Y Merkezleniyor",
    CycleState.RECOVERY_CLAMP_UP: "Toparlanma: Baskı Kalkıyor",
    CycleState.FAULT: "Arıza",
}

# Cycle states in which manual jog / feed commands must be refused client-side
# (the real interlock lives in the PLC; this only drives UI enable/disable).
AUTO_CYCLE_ACTIVE_STATES = frozenset(
    {
        CycleState.AUTO_START_CHECK,
        CycleState.CLAMP_DOWN,
        CycleState.WAIT_VISION_LINE,
        CycleState.BLADE_DOWN,
        CycleState.CUTTING,
        CycleState.CUT_FINISH,
        CycleState.BLADE_UP,
        CycleState.RETURN_X_Y,
        CycleState.CLAMP_UP,
    }
)

RECOVERY_STATES = frozenset(
    {
        CycleState.CUT_INTERRUPTED,
        CycleState.RECOVERY,
        CycleState.RECOVERY_BLADE_UP,
        CycleState.RECOVERY_RETURN_X,
        CycleState.RECOVERY_CENTER_Y,
        CycleState.RECOVERY_CLAMP_UP,
    }
)


def cycle_state_label(value: int) -> str:
    """Turkish label for a raw CycleState int; unknown codes degrade gracefully."""
    try:
        state = CycleState(value)
    except ValueError:
        return f"Bilinmeyen Durum ({value})"
    return CYCLE_STATE_LABELS_TR[state]
