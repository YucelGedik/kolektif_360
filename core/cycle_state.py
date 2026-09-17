"""Single source of truth for PLC `eMachineState` codes and their Turkish
labels.

Codes and labels come from the confirmed HMI/PLC integration task plan
(`docs/BUFERA_HMI_PLC_ENTEGRASYON_GOREV_PLANI.md`, section 5) and the
2026-09-16 approval that fixed them exactly as below — these are no longer
provisional. UI code must never display a raw integer; it must always go
through `cycle_state_label`.
"""

from __future__ import annotations

from enum import IntEnum


class CycleState(IntEnum):
    INIT = 0
    MANUAL = 10
    WAIT_FOR_MATERIAL = 20
    CLAMP_DOWN = 30
    WAIT_VISION = 40
    ALIGN_Y = 50
    WAIT_BLADE_REQUEST = 60
    BLADE_DOWN = 70
    CUTTING = 80
    BLADE_UP = 90
    RETURN_AXES = 100
    CLAMP_UP = 110
    CYCLE_COMPLETE = 120

    STOPPING = 500
    RECOVERY = 510

    FAULT = 900


CYCLE_STATE_LABELS_TR: dict[CycleState, str] = {
    CycleState.INIT: "Başlatılıyor",
    CycleState.MANUAL: "Manuel",
    CycleState.WAIT_FOR_MATERIAL: "Perde Bekliyor",
    CycleState.CLAMP_DOWN: "Baskı İniyor",
    CycleState.WAIT_VISION: "Kamera Bekleniyor",
    CycleState.ALIGN_Y: "Y Hizalanıyor",
    CycleState.WAIT_BLADE_REQUEST: "Bıçak Talebi Bekleniyor",
    CycleState.BLADE_DOWN: "Bıçak İniyor",
    CycleState.CUTTING: "Kesim",
    CycleState.BLADE_UP: "Bıçak Kalkıyor",
    CycleState.RETURN_AXES: "Eksenler Dönüyor",
    CycleState.CLAMP_UP: "Baskı Kalkıyor",
    CycleState.CYCLE_COMPLETE: "Çevrim Tamamlandı",
    CycleState.STOPPING: "Durduruluyor",
    CycleState.RECOVERY: "Recovery",
    CycleState.FAULT: "Arıza",
}

# Cycle states in which manual jog / feed commands must be refused client-side
# (the real interlock lives in the PLC; this only drives UI enable/disable).
# NOTE: membership here is provisional pending Faz 6 (manual/jog write handshake);
# this set only needs to stay referentially valid for Faz 1 (read binding).
AUTO_CYCLE_ACTIVE_STATES = frozenset(
    {
        CycleState.WAIT_FOR_MATERIAL,
        CycleState.CLAMP_DOWN,
        CycleState.WAIT_VISION,
        CycleState.ALIGN_Y,
        CycleState.WAIT_BLADE_REQUEST,
        CycleState.BLADE_DOWN,
        CycleState.CUTTING,
        CycleState.BLADE_UP,
        CycleState.RETURN_AXES,
        CycleState.CLAMP_UP,
    }
)

RECOVERY_STATES = frozenset(
    {
        CycleState.STOPPING,
        CycleState.RECOVERY,
    }
)


def cycle_state_label(value: int) -> str:
    """Turkish label for a raw CycleState int; unknown codes degrade gracefully."""
    try:
        state = CycleState(value)
    except ValueError:
        return f"Bilinmeyen Durum ({value})"
    return CYCLE_STATE_LABELS_TR[state]
