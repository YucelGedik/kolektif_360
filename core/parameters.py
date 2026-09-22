"""Engineering parameter definitions for the Settings screen.

2026-09-16: replaced with the real CODESYS GVL parameter set (`lr*`/`t*`
tags), confirmed against the actual PLC GVL and Logic_Control by the user.
`key` is the logical name used everywhere else (tag map, param cache,
SettingsStore) - it mirrors the real tag name so the mapping is obvious.
`default` values below are the REAL current PLC defaults the user read out
of the GVL directly (same day) - used as the Demo-mode simulated value and
as the placeholder shown for the brief "Okunuyor…" window before the first
real PLC read confirms it.

Min/max ranges bound the Settings screen's QDoubleSpinBox - a value outside
[min_value, max_value] gets silently CLAMPED by Qt when displayed (this bit
us once already: Y Yazılım Max's range was guessed at 0..24 from an
unrelated Vision document, so the real PLC value of 30 kept showing as a
clamped 24 even though the read itself was correct). Most ranges here are
still a generous, non-mechanical guess. The exception is the 6 velocity
fields (X Kesim/Dönüş/Jog Hızı, Y Pozisyonlama/Follow Maks./Jog Hızı):
2026-09-22, kullanıcı gerçek mekaniğe bağlanıp final sınırları onayladı -
bu 6 alanın max_value'su artık gerçek mekanik limit, tahmin DEĞİL.

Pneumatic delays (clamp/blade down/up) and the "advanced" motion tuning
parameters (`lrMaxAllowedSlope`, `lrStopAccDec`, `lrPositionTolerance`,
`lrStopVelocityTolerance`) are intentionally NOT in this list yet - the
first because Logic_Control still hard-codes them (T#500ms, no GVL tag),
the second because the user asked to keep them out of the main Settings
list for now.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    key: str  # matches the tag map / config node key (mirrors the real GVL name)
    label_tr: str
    unit: str
    default: float
    min_value: float
    max_value: float


PARAMETER_SPECS: list[ParameterSpec] = [
    # 2026-09-22 (kullanıcı isteği): "HIZ SINIRLARINI BU ŞEKİLDE REVİZE ET
    # MEKANİĞE BAĞLANDIK VE BU SINIRLARA KARAR VERDİK" - aşağıdaki 6 hız
    # alanının min/max'ı artık genel/güvenli bir tahmin değil, gerçek
    # mekanik test sonrası onaylanmış nihai sınır. Diğer alanlar (Acc/Dec,
    # konum, timeout) bu revizyonun kapsamı dışında, değişmedi.
    ParameterSpec("lr_x_cut_velocity", "X Kesim Hızı", "mm/s", 175.0, 1.0, 800.0),
    ParameterSpec("lr_x_cut_acc_dec", "X Kesim Acc/Dec", "mm/s²", 500.0, 1.0, 10000.0),
    ParameterSpec("lr_x_return_velocity", "X Dönüş Hızı", "mm/s", 400.0, 1.0, 1060.0),
    ParameterSpec("lr_x_return_acc_dec", "X Dönüş Acc/Dec", "mm/s²", 500.0, 1.0, 10000.0),
    ParameterSpec("lr_x_cut_start_pos", "X Kesim Başlangıç", "mm", 0.0, 0.0, 3600.0),
    ParameterSpec("lr_x_cut_end_pos", "X Kesim Bitiş", "mm", 3600.0, 0.0, 3600.0),
    ParameterSpec("lr_y_center_position", "Y Merkez Konum", "mm", 0.0, -50.0, 50.0),
    ParameterSpec("lr_y_software_min", "Y Yazılım Min", "mm", -30.0, -50.0, 0.0),
    ParameterSpec("lr_y_software_max", "Y Yazılım Max", "mm", 30.0, 0.0, 50.0),
    ParameterSpec("lr_y_move_velocity", "Y Pozisyonlama Hızı", "mm/s", 10.0, 1.0, 50.0),
    ParameterSpec("lr_y_move_acc_dec", "Y Pozisyonlama Acc/Dec", "mm/s²", 100.0, 1.0, 10000.0),
    ParameterSpec("lr_y_max_velocity", "Y Follow Maks. Hızı", "mm/s", 5.0, 1.0, 50.0),
    ParameterSpec("lr_x_jog_velocity", "X Jog Hızı", "mm/s", 50.0, 1.0, 400.0),
    ParameterSpec("lr_y_jog_velocity", "Y Jog Hızı", "mm/s", 5.0, 1.0, 50.0),
    ParameterSpec("lr_jog_acc_dec", "Jog Acc/Dec", "mm/s²", 100.0, 1.0, 10000.0),
    ParameterSpec("t_vision_heartbeat_timeout", "Heartbeat Zaman Aşımı", "ms", 2000.0, 10.0, 10000.0),
]
