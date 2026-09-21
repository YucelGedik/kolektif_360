"""Demo/simulation mode: drives a MachineSnapshot through the normal cycle
described in the integration brief (section 6) plus a stop/recovery path
(section 17) and one scripted alarm, without any real PLC/OPC UA connection.

Used by MachineService whenever `config/opcua.json` has no endpoint
configured, so the screens can be developed and demoed standalone
(acceptance criterion: fake/demo snapshot works without real PLC tags).
"""

from __future__ import annotations

import random

from core.cycle_state import AUTO_CYCLE_ACTIVE_STATES, CycleState
from core.models import MachineSnapshot
from core.parameters import PARAMETER_SPECS

IDLE_ALARM_DELAY_S = 8.0
# PLC-HMI-20260921-10/11 (C5): demo-only, kısa tutulur (gerçek PLC hareket
# süresini taklit etmiyor - yalnız Busy->Done geçişini göstermek için).
MOVE_TO_START_DURATION_S = 0.6


class DemoSimulator:
    def __init__(self) -> None:
        self.params: dict[str, float] = {spec.key: spec.default for spec in PARAMETER_SPECS}

        self.phase_elapsed = 0.0
        self.auto_mode = False
        self.manual_mode = True

        self.jog_x_dir = 0
        self.jog_y_dir = 0
        self.jog_x_fast = False
        self.jog_y_fast = False
        self.blade_retract_requested = False
        self.clamp_retract_requested = False
        self.blade_down_requested = False
        self.clamp_down_requested = False
        self.y_center_requested = False
        self.move_to_start_requested = False
        self.move_to_start_remaining = 0.0

        self.start_requested = False
        self.stop_requested = False
        self.reset_requested = False

        self.idle_alarm_timer = 0.0
        self.alarm_fired_once = False

    def apply_initial(self, snap: MachineSnapshot) -> None:
        snap.machine_ready = True
        snap.x_servo_ready = True
        snap.y_servo_ready = True
        snap.vision_ready = True
        snap.vision_heartbeat_ok = True
        snap.line_valid = False
        snap.manual_mode = True
        snap.auto_mode = False
        snap.start_permitted = True
        snap.clamp_up = True
        snap.blade_up = True
        snap.feed_manual_allowed = True
        snap.cycle_state = int(CycleState.MANUAL)

    # -- commands from MachineService (UI thread) ------------------------

    def request_start(self) -> None:
        self.start_requested = True

    def request_stop(self) -> None:
        self.stop_requested = True

    def request_reset(self) -> None:
        self.reset_requested = True

    def set_mode(self, auto: bool) -> None:
        self.auto_mode = auto
        self.manual_mode = not auto

    def set_jog_x(self, direction: int, active: bool, fast: bool = False) -> None:
        self.jog_x_dir = direction if active else 0
        self.jog_x_fast = fast

    def set_jog_y(self, direction: int, active: bool, fast: bool = False) -> None:
        self.jog_y_dir = direction if active else 0
        self.jog_y_fast = fast

    def request_y_center(self) -> None:
        self.y_center_requested = True

    def request_blade_retract(self) -> None:
        self.blade_retract_requested = True

    def request_clamp_retract(self) -> None:
        self.clamp_retract_requested = True

    def request_blade_down(self) -> None:
        self.blade_down_requested = True

    def request_clamp_down(self) -> None:
        self.clamp_down_requested = True

    def request_move_to_start(self) -> None:
        self.move_to_start_requested = True

    # -- simulation tick ---------------------------------------------------

    def tick(self, dt: float, snap: MachineSnapshot, alarms, notify_alarms) -> None:
        snap.auto_mode = self.auto_mode
        snap.manual_mode = self.manual_mode

        try:
            phase = CycleState(snap.cycle_state)
        except ValueError:
            phase = CycleState.MANUAL if self.manual_mode else CycleState.WAIT_FOR_MATERIAL

        # MANUAL is only ever shown while xManualMode is TRUE (gorev plani
        # duzeltmesi, 2026-09-16); the auto-mode resting/idle state is
        # WAIT_FOR_MATERIAL instead.
        if phase == CycleState.MANUAL and not self.manual_mode:
            phase = CycleState.WAIT_FOR_MATERIAL
            self._enter(snap, phase)
        elif phase == CycleState.WAIT_FOR_MATERIAL and self.manual_mode:
            phase = CycleState.MANUAL
            self._enter(snap, phase)

        self._apply_manual_controls(snap, phase)
        self._apply_move_to_start(dt, snap, phase)

        idle = phase in (CycleState.MANUAL, CycleState.WAIT_FOR_MATERIAL)
        if idle and not snap.alarm_active and not self.alarm_fired_once:
            self.idle_alarm_timer += dt
            if self.idle_alarm_timer >= IDLE_ALARM_DELAY_S:
                self._raise_demo_alarm(snap, alarms, notify_alarms)
                return

        if self.reset_requested:
            self.reset_requested = False
            if snap.alarm_active:
                self._clear_demo_alarm(snap, alarms, notify_alarms)
                return

        if phase == CycleState.FAULT:
            return  # wait for Reset

        if self.stop_requested:
            self.stop_requested = False
            if phase in AUTO_CYCLE_ACTIVE_STATES:
                self._enter(snap, CycleState.STOPPING)
                return

        if self.start_requested:
            self.start_requested = False
            if phase == CycleState.WAIT_FOR_MATERIAL and snap.start_permitted:
                snap.cycle_active = True
                self._enter(snap, CycleState.CLAMP_DOWN)
                return

        self.phase_elapsed += dt
        self._advance_phase(dt, snap, phase)

    def _apply_manual_controls(self, snap: MachineSnapshot, phase: CycleState) -> None:
        if not (self.manual_mode and phase not in AUTO_CYCLE_ACTIVE_STATES):
            return
        cut_end = self.params["lr_x_cut_end_pos"]
        if self.jog_x_dir:
            x_speed = 90.0 if self.jog_x_fast else 30.0
            snap.x_actual_pos = max(0.0, min(cut_end, snap.x_actual_pos + self.jog_x_dir * x_speed * 0.05))
        if self.jog_y_dir:
            lo, hi = self.params["lr_y_software_min"], self.params["lr_y_software_max"]
            y_speed = 30.0 if self.jog_y_fast else 10.0
            snap.y_actual_pos = max(lo, min(hi, snap.y_actual_pos + self.jog_y_dir * y_speed * 0.05))
            snap.y_set_pos = snap.y_actual_pos
        if self.y_center_requested:
            snap.y_actual_pos = self.params["lr_y_center_position"]
            snap.y_set_pos = snap.y_actual_pos
            self.y_center_requested = False
        # PLC-HMI-20260921-09: aynı mekanizmanın iki talebi birlikte gelirse
        # Yukarı öncelikli; Aşağı kabul edilince o mekanizmanın Yukarı-kabul
        # biti FALSE olur (ayrı bir Aşağı-kabul biti yok - bilinçli tasarım).
        if self.blade_retract_requested or self.blade_down_requested:
            if self.blade_retract_requested:
                snap.blade_down, snap.blade_up = False, True
                snap.blade_retract_accepted = True
            else:
                snap.blade_down, snap.blade_up = True, False
                snap.blade_retract_accepted = False
            self.blade_retract_requested = False
            self.blade_down_requested = False
        if self.clamp_retract_requested or self.clamp_down_requested:
            if self.clamp_retract_requested:
                snap.clamp_down, snap.clamp_up = False, True
                snap.clamp_retract_accepted = True
            else:
                snap.clamp_down, snap.clamp_up = True, False
                snap.clamp_retract_accepted = False
            self.clamp_retract_requested = False
            self.clamp_down_requested = False

    def _apply_move_to_start(self, dt: float, snap: MachineSnapshot, phase: CycleState) -> None:
        """PLC-HMI-20260921-10/11 (C5): demo tarafı "İzin HMI'da yeniden
        üretilmez" ilkesini burada bile korur - `Allowed`'ı PLC'nin gerçek
        ön koşuluna yakın (manuel + otomatik çevrim dışı + iki mekanizma
        kalkık + zaten meşgul değil) her tick yeniden hesaplar, yalnız
        `request_move_to_start()` bunu tekrar sorgulamaz."""
        snap.move_to_start_allowed = (
            self.manual_mode
            and phase not in AUTO_CYCLE_ACTIVE_STATES
            and snap.blade_up
            and snap.clamp_up
            and not snap.move_to_start_busy
        )

        if self.move_to_start_requested:
            self.move_to_start_requested = False
            if snap.move_to_start_allowed:
                snap.move_to_start_busy = True
                snap.move_to_start_allowed = False
                snap.move_to_start_done = False
                snap.move_to_start_aborted = False
                snap.move_to_start_error = False
                self.move_to_start_remaining = MOVE_TO_START_DURATION_S
            else:
                snap.move_to_start_aborted = True

        if snap.move_to_start_busy:
            self.move_to_start_remaining -= dt
            if self.move_to_start_remaining <= 0:
                snap.x_actual_pos = self.params["lr_x_cut_start_pos"]
                snap.y_actual_pos = self.params["lr_y_center_position"]
                snap.y_set_pos = snap.y_actual_pos
                snap.move_to_start_busy = False
                snap.move_to_start_done = True

    def _advance_phase(self, dt: float, snap: MachineSnapshot, phase: CycleState) -> None:
        p = self.params

        # WAIT_FOR_MATERIAL is a resting state; it only leaves on an explicit
        # start request (handled in tick()), never on a timer.
        if phase == CycleState.CLAMP_DOWN and self.phase_elapsed >= 0.4:
            snap.clamp_down, snap.clamp_up = True, False
            self._enter(snap, CycleState.WAIT_VISION)
        elif phase == CycleState.WAIT_VISION and self.phase_elapsed >= 0.3:
            snap.line_valid = True
            self._enter(snap, CycleState.ALIGN_Y)
        elif phase == CycleState.ALIGN_Y and self.phase_elapsed >= 0.2:
            self._enter(snap, CycleState.WAIT_BLADE_REQUEST)
        elif phase == CycleState.WAIT_BLADE_REQUEST and self.phase_elapsed >= 0.15:
            self._enter(snap, CycleState.BLADE_DOWN)
        elif phase == CycleState.BLADE_DOWN and self.phase_elapsed >= 0.4:
            snap.blade_down, snap.blade_up = True, False
            snap.x_actual_pos = 0.0
            self._enter(snap, CycleState.CUTTING)

        elif phase == CycleState.CUTTING:
            cut_start = p["lr_x_cut_start_pos"]
            cut_end = p["lr_x_cut_end_pos"]
            vel = p["lr_x_cut_velocity"]
            snap.x_actual_vel = vel
            snap.x_actual_pos = min(cut_end, snap.x_actual_pos + vel * dt)
            span = cut_end - cut_start
            t = (snap.x_actual_pos - cut_start) / span if span else 1.0
            target_y = -12.0 + 24.0 * t + random.uniform(-0.3, 0.3)
            snap.y_set_pos = target_y
            snap.y_actual_pos = target_y
            snap.y_set_vel = (24.0 / span * vel) if span else 0.0
            snap.vision_target_x = min(cut_end, snap.x_actual_pos + 50.0)
            snap.vision_target_y = target_y
            snap.vision_slope = (24.0 / span) if span else 0.0
            snap.vision_confidence = random.uniform(0.93, 0.99)
            # Gorev plani duzeltmesi (2026-09-16): ilerleme kesin olarak
            # (ActualX_mm - lrX_CutStartPos) / (CutEndX_mm - lrX_CutStartPos),
            # %0-100 clamp.
            snap.cycle_progress = max(0.0, min(100.0, t * 100.0))
            if snap.x_actual_pos >= cut_end:
                snap.x_actual_vel = 0.0
                self._enter(snap, CycleState.BLADE_UP)

        elif phase == CycleState.BLADE_UP and self.phase_elapsed >= 0.4:
            snap.blade_down, snap.blade_up = False, True
            self._enter(snap, CycleState.RETURN_AXES)

        elif phase == CycleState.RETURN_AXES:
            self._return_axes(dt, snap)
            if snap.x_actual_pos <= 0.001 and abs(snap.y_actual_pos - p["lr_y_center_position"]) < 0.05:
                snap.x_actual_pos, snap.x_actual_vel = 0.0, 0.0
                snap.y_actual_pos = p["lr_y_center_position"]
                snap.line_valid = False
                self._enter(snap, CycleState.CLAMP_UP)

        elif phase == CycleState.CLAMP_UP and self.phase_elapsed >= 0.4:
            snap.clamp_down, snap.clamp_up = False, True
            self._enter(snap, CycleState.CYCLE_COMPLETE)
        elif phase == CycleState.CYCLE_COMPLETE and self.phase_elapsed >= 0.3:
            snap.cycle_active = False
            snap.cycle_progress = 0.0
            self._enter(snap, CycleState.WAIT_FOR_MATERIAL)

        # Normal STOP: STOPPING -> BLADE_UP -> RETURN_AXES -> CLAMP_UP ->
        # CYCLE_COMPLETE -> WAIT_FOR_MATERIAL (shares the same tail as a
        # completed cycle - no separate recovery sub-machine).
        elif phase == CycleState.STOPPING and self.phase_elapsed >= 0.3:
            self._enter(snap, CycleState.BLADE_UP)

        # Fault reset: FAULT -> RECOVERY -> BLADE_UP -> ... -> WAIT_FOR_MATERIAL
        # (same shared tail, entered only after an operator Reset).
        elif phase == CycleState.RECOVERY and self.phase_elapsed >= 0.2:
            self._enter(snap, CycleState.BLADE_UP)

    def _return_axes(self, dt: float, snap: MachineSnapshot) -> None:
        ret_vel = self.params["lr_x_return_velocity"]
        snap.x_actual_vel = -ret_vel
        snap.x_actual_pos = max(0.0, snap.x_actual_pos - ret_vel * dt)
        center = self.params["lr_y_center_position"]
        snap.y_actual_pos += (center - snap.y_actual_pos) * min(1.0, dt * 3.0)
        snap.y_set_pos = snap.y_actual_pos
        snap.cycle_progress = 0.0

    def _enter(self, snap: MachineSnapshot, state: CycleState) -> None:
        snap.cycle_state = int(state)
        self.phase_elapsed = 0.0

    def _raise_demo_alarm(self, snap: MachineSnapshot, alarms, notify_alarms) -> None:
        alarms.raise_alarm(1201, "VISION")
        snap.alarm_active = True
        snap.alarm_code = 1201
        snap.alarm_count = alarms.active_count()
        snap.vision_heartbeat_ok = False
        snap.start_permitted = False
        snap.cycle_state = int(CycleState.FAULT)
        # Gerçek PLC her yeni FAULT'ta bu kabul bitlerini sıfırlar
        # (PLC-HMI-20260918-06) - demo aynı davranışı taklit eder.
        snap.blade_retract_accepted = False
        snap.clamp_retract_accepted = False
        self.alarm_fired_once = True
        notify_alarms()

    def _clear_demo_alarm(self, snap: MachineSnapshot, alarms, notify_alarms) -> None:
        alarms.clear_active()
        snap.alarm_active = False
        snap.alarm_code = 0
        snap.alarm_count = 0
        snap.vision_heartbeat_ok = True
        snap.start_permitted = True
        # Fault reset: FAULT -> RECOVERY -> BLADE_UP -> RETURN_AXES ->
        # CLAMP_UP -> CYCLE_COMPLETE -> WAIT_FOR_MATERIAL (gorev plani
        # duzeltmesi, 2026-09-16). cycle_active stays True through the tail
        # even though this demo alarm only fires from idle.
        snap.cycle_active = True
        self._enter(snap, CycleState.RECOVERY)
        notify_alarms()
