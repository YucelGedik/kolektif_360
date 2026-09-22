"""Shared, framework-agnostic data model for one PLC snapshot.

This extends the dataclass suggested in the integration brief (section 19)
with the additional fields the Manual/Service, Settings and Alarm screens
need. Kept dependency-free (no Qt, no asyncua) so it can be reused by the
PLC layer, the service layer and the UI layer alike.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class ConnectionState:
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    DEGRADED = "Degraded"
    ERROR = "Error"
    DEMO = "Demo"


@dataclass(slots=True)
class MachineSnapshot:
    timestamp: float = field(default_factory=time.monotonic)
    connection_state: str = ConnectionState.DISCONNECTED
    stale: bool = True

    machine_ready: bool = False
    auto_mode: bool = False
    manual_mode: bool = False
    cycle_active: bool = False
    cut_active: bool = False
    cycle_state: int = 0
    cycle_progress: float = 0.0
    start_permitted: bool = False
    emergency_active: bool = False
    trajectory_fault: bool = False
    trajectory_valid: bool = False
    lr_max_allowed_slope: float = 0.0

    # PLC-HMI-20260921-09: manuel bıçak/baskı pulse butonlarının "ortak izin"
    # kontrolü için - GVL.xEmergencyOK/xAlarmStopRequest/xMotionStop.
    # xEmergencyOK, EmergencyState'in tersi kutupta ayrı bir tag (TRUE=saglikli).
    emergency_ok: bool = True
    alarm_stop_request: bool = False
    motion_stop: bool = False

    # PLC-HMI-20260921-10/11 (C5, "Başlangıç Konumuna Dön"): X+Y'yi ayarlı
    # başlangıç konumuna otomatik götüren tek PLC hareketinin salt okunur
    # durum bitleri. Allowed PLC'nin nihai izni - HMI bunu yeniden üretmez.
    move_to_start_allowed: bool = False
    move_to_start_busy: bool = False
    move_to_start_done: bool = False
    move_to_start_aborted: bool = False
    move_to_start_error: bool = False

    x_servo_ready: bool = False
    x_fault: bool = False
    x_fault_code: int = 0
    x_actual_pos: float = 0.0
    x_actual_vel: float = 0.0
    x_cut_velocity: float = 175.0
    x_at_start: bool = False

    y_servo_ready: bool = False
    y_fault: bool = False
    y_fault_code: int = 0
    y_actual_pos: float = 0.0
    y_actual_vel: float = 0.0
    y_set_pos: float = 0.0
    y_set_vel: float = 0.0
    y_at_center: bool = False

    clamp_down: bool = False
    clamp_up: bool = True
    blade_down: bool = False
    blade_up: bool = True
    # PLC-HMI-20260918-06: PLC-üretimli, salt okunur "kabul" bitleri - HMI
    # bunları hiç yazmaz, yalnız gösterir. FAULT'ta PLC tarafından sıfırlanır.
    blade_retract_accepted: bool = False
    clamp_retract_accepted: bool = False
    # PLC-HMI-20260921-09: Aşağı taleplerine PLC-üretimli bir "kabul" biti
    # yok (bilinçli tasarım - önceki not: "Yeni asagi-kabul biti eklenmedi").
    # Hazırlıkta Aşağı pasif, Yukarı serbest kalmalı - HMI bu bayrağa göre gater.
    manual_preparation_required: bool = False

    feed_forward_input: bool = False
    feed_reverse_input: bool = False
    feed_running: bool = False
    feed_complete: bool = False
    feed_manual_allowed: bool = True

    vision_ready: bool = False
    line_valid: bool = False
    vision_fault: bool = False
    vision_heartbeat_ok: bool = False
    vision_target_x: float = 0.0
    vision_target_y: float = 0.0
    vision_confidence: float = 0.0
    vision_slope: float = 0.0
    vision_cut_permit: bool = False
    vision_z_down_request: bool = False
    vision_heartbeat: int = 0
    vision_sequence: int = 0

    alarm_active: bool = False
    alarm_code: int = 0
    alarm_count: int = 0

    # PLC-HMI-20260921-16 (C6.1 Hata/Uyarı/Mesaj kataloğu): PLC-üretimli,
    # latched HATA bitleri - yalnız xAlarmResetAccepted (gerçek Reset kabulü)
    # ile FALSE olurlar, HMI'nin kendi Reset tıklaması ile değil.
    alarm_clamp_lost_during_cut: bool = False
    alarm_blade_lost_during_cut: bool = False
    alarm_clamp_down_timeout: bool = False
    alarm_blade_down_timeout: bool = False

    # Zaten var olan GVL motion hata bitleri - önceden HMI'ya hiç okunmuyordu.
    x_cut_error: bool = False
    x_return_error: bool = False
    y_move_error: bool = False
    y_follow_error: bool = False

    # C6.1: PLC'nin aday 5 yeni RO tag'i - PLC-HMI-20260922-18 (C06_1 audit)
    # ile export'ta VAR olduğu doğrulandı, yalnız online node/erişim testi
    # hâlâ bekliyor - config'te eşleme olmadığı sürece hep False kalır
    # (güvenli varsayılan, C0.4/C5 dersi). Online doğrulanınca gerçek
    # config'e eklenecek.
    operator_stop_active: bool = False
    x_stop_error: bool = False
    y_stop_error: bool = False
    x_axis_error: bool = False
    y_axis_error: bool = False

    # PLC-HMI-20260922-17 (C6 toplu teslim): 3 yeni aday latched HATA bit'i
    # (xAlarmModeChangedDuringCycle/xAlarmClampLostDuringCycle/
    # xAlarmBladeNotClearDuringReturn) - kod/test teslim edildi; PLC-HMI-
    # 20260922-18 (C06_1 audit) ile export'ta VAR olduğu doğrulandı, yalnız
    # online node/erişim testi hâlâ bekliyor. Aynı disiplin: config'te
    # eşleme olmadığı sürece hep False kalır, online doğrulanınca gerçek
    # config'e eklenecek.
    alarm_mode_changed_during_cycle: bool = False
    alarm_clamp_lost_during_cycle: bool = False
    alarm_blade_not_clear_during_return: bool = False
