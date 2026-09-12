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
    cycle_state: int = 0
    cycle_progress: float = 0.0
    start_permitted: bool = False

    estop_ok: bool = False
    safety_ok: bool = False

    x_servo_ready: bool = False
    x_fault: bool = False
    x_fault_code: int = 0
    x_actual_pos: float = 0.0
    x_actual_vel: float = 0.0
    x_cut_velocity: float = 175.0

    y_servo_ready: bool = False
    y_fault: bool = False
    y_fault_code: int = 0
    y_actual_pos: float = 0.0
    y_set_pos: float = 0.0
    y_set_vel: float = 0.0

    clamp_down: bool = False
    clamp_up: bool = True
    blade_down: bool = False
    blade_up: bool = True

    feed_forward_input: bool = False
    feed_reverse_input: bool = False
    feed_running: bool = False
    feed_manual_allowed: bool = True

    vision_ready: bool = False
    line_valid: bool = False
    vision_fault: bool = False
    vision_heartbeat_ok: bool = False
    vision_target_x: float = 0.0
    vision_target_y: float = 0.0
    vision_confidence: float = 0.0
    vision_slope: float = 0.0

    alarm_active: bool = False
    alarm_code: int = 0
    alarm_count: int = 0
