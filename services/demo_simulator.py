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
        self.blade_cmd: str | None = None
        self.clamp_cmd: str | None = None
        self.y_center_requested = False

        self.start_requested = False
        self.stop_requested = False
        self.reset_requested = False

        self.idle_alarm_timer = 0.0
        self.alarm_fired_once = False

    def apply_initial(self, snap: MachineSnapshot) -> None:
        snap.machine_ready = True
        snap.estop_ok = True
        snap.safety_ok = True
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
        snap.cycle_state = int(CycleState.IDLE)

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

    def set_blade(self, down: bool, active: bool) -> None:
        wanted = "down" if down else "up"
        if active:
            self.blade_cmd = wanted
        elif self.blade_cmd == wanted:
            self.blade_cmd = None

    def set_clamp(self, down: bool, active: bool) -> None:
        wanted = "down" if down else "up"
        if active:
            self.clamp_cmd = wanted
        elif self.clamp_cmd == wanted:
            self.clamp_cmd = None

    # -- simulation tick ---------------------------------------------------

    def tick(self, dt: float, snap: MachineSnapshot, alarms, notify_alarms) -> None:
        snap.auto_mode = self.auto_mode
        snap.manual_mode = self.manual_mode

        try:
            phase = CycleState(snap.cycle_state)
        except ValueError:
            phase = CycleState.IDLE

        self._apply_manual_controls(snap, phase)

        if phase == CycleState.IDLE and not snap.alarm_active and not self.alarm_fired_once:
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
                interrupted = phase == CycleState.CUTTING
                self._enter(snap, CycleState.CUT_INTERRUPTED if interrupted else CycleState.CONTROLLED_STOP)
                return

        if self.start_requested:
            self.start_requested = False
            if phase == CycleState.IDLE and snap.start_permitted:
                snap.cycle_active = True
                self._enter(snap, CycleState.AUTO_START_CHECK)
                return

        self.phase_elapsed += dt
        self._advance_phase(dt, snap, phase)

    def _apply_manual_controls(self, snap: MachineSnapshot, phase: CycleState) -> None:
        if not (self.manual_mode and phase not in AUTO_CYCLE_ACTIVE_STATES):
            return
        cut_end = self.params["par_x_cut_end_pos"]
        if self.jog_x_dir:
            x_speed = 90.0 if self.jog_x_fast else 30.0
            snap.x_actual_pos = max(0.0, min(cut_end, snap.x_actual_pos + self.jog_x_dir * x_speed * 0.05))
        if self.jog_y_dir:
            lo, hi = self.params["par_y_software_min"], self.params["par_y_software_max"]
            y_speed = 30.0 if self.jog_y_fast else 10.0
            snap.y_actual_pos = max(lo, min(hi, snap.y_actual_pos + self.jog_y_dir * y_speed * 0.05))
            snap.y_set_pos = snap.y_actual_pos
        if self.y_center_requested:
            snap.y_actual_pos = self.params["par_y_center_pos"]
            snap.y_set_pos = snap.y_actual_pos
            self.y_center_requested = False
        if self.blade_cmd == "down":
            snap.blade_down, snap.blade_up = True, False
        elif self.blade_cmd == "up":
            snap.blade_down, snap.blade_up = False, True
        if self.clamp_cmd == "down":
            snap.clamp_down, snap.clamp_up = True, False
        elif self.clamp_cmd == "up":
            snap.clamp_down, snap.clamp_up = False, True

    def _advance_phase(self, dt: float, snap: MachineSnapshot, phase: CycleState) -> None:
        p = self.params

        if phase == CycleState.AUTO_START_CHECK and self.phase_elapsed >= 0.3:
            self._enter(snap, CycleState.CLAMP_DOWN)
        elif phase == CycleState.CLAMP_DOWN and self.phase_elapsed >= 0.4:
            snap.clamp_down, snap.clamp_up = True, False
            self._enter(snap, CycleState.WAIT_VISION_LINE)
        elif phase == CycleState.WAIT_VISION_LINE and self.phase_elapsed >= 0.3:
            snap.line_valid = True
            self._enter(snap, CycleState.BLADE_DOWN)
        elif phase == CycleState.BLADE_DOWN and self.phase_elapsed >= 0.4:
            snap.blade_down, snap.blade_up = True, False
            snap.x_actual_pos = 0.0
            self._enter(snap, CycleState.CUTTING)

        elif phase == CycleState.CUTTING:
            cut_end = p["par_x_cut_end_pos"]
            vel = p["par_x_cut_velocity"]
            snap.x_actual_vel = vel
            snap.x_actual_pos = min(cut_end, snap.x_actual_pos + vel * dt)
            t = snap.x_actual_pos / cut_end if cut_end else 1.0
            target_y = -12.0 + 24.0 * t + random.uniform(-0.3, 0.3)
            snap.y_set_pos = target_y
            snap.y_actual_pos = target_y
            snap.y_set_vel = (24.0 / cut_end * vel) if cut_end else 0.0
            snap.vision_target_x = min(cut_end, snap.x_actual_pos + 50.0)
            snap.vision_target_y = target_y
            snap.vision_slope = (24.0 / cut_end) if cut_end else 0.0
            snap.vision_confidence = random.uniform(0.93, 0.99)
            snap.cycle_progress = t * 100.0
            if snap.x_actual_pos >= cut_end:
                self._enter(snap, CycleState.CUT_FINISH)

        elif phase == CycleState.CUT_FINISH and self.phase_elapsed >= 0.2:
            snap.x_actual_vel = 0.0
            self._enter(snap, CycleState.BLADE_UP)
        elif phase == CycleState.BLADE_UP and self.phase_elapsed >= 0.4:
            snap.blade_down, snap.blade_up = False, True
            self._enter(snap, CycleState.RETURN_X_Y)

        elif phase == CycleState.RETURN_X_Y:
            self._return_axes(dt, snap)
            if snap.x_actual_pos <= 0.001 and abs(snap.y_actual_pos - p["par_y_center_pos"]) < 0.05:
                snap.x_actual_pos, snap.x_actual_vel = 0.0, 0.0
                snap.y_actual_pos = p["par_y_center_pos"]
                snap.line_valid = False
                self._enter(snap, CycleState.CLAMP_UP)

        elif phase == CycleState.CLAMP_UP and self.phase_elapsed >= 0.4:
            snap.clamp_down, snap.clamp_up = False, True
            self._enter(snap, CycleState.CYCLE_COMPLETE)
        elif phase == CycleState.CYCLE_COMPLETE and self.phase_elapsed >= 0.3:
            snap.cycle_active = False
            snap.cycle_progress = 0.0
            self._enter(snap, CycleState.IDLE)

        elif phase in (CycleState.CONTROLLED_STOP, CycleState.CUT_INTERRUPTED) and self.phase_elapsed >= 0.3:
            self._enter(snap, CycleState.RECOVERY)
        elif phase == CycleState.RECOVERY and self.phase_elapsed >= 0.2:
            self._enter(snap, CycleState.RECOVERY_BLADE_UP)
        elif phase == CycleState.RECOVERY_BLADE_UP:
            snap.blade_down, snap.blade_up = False, True
            if self.phase_elapsed >= 0.4:
                self._enter(snap, CycleState.RECOVERY_RETURN_X)
        elif phase == CycleState.RECOVERY_RETURN_X:
            snap.x_actual_pos = max(0.0, snap.x_actual_pos - p["par_x_return_velocity"] * dt)
            if snap.x_actual_pos <= 0.001:
                snap.x_actual_pos = 0.0
                self._enter(snap, CycleState.RECOVERY_CENTER_Y)
        elif phase == CycleState.RECOVERY_CENTER_Y:
            center = p["par_y_center_pos"]
            snap.y_actual_pos += (center - snap.y_actual_pos) * min(1.0, dt * 3.0)
            snap.y_set_pos = snap.y_actual_pos
            if abs(snap.y_actual_pos - center) < 0.05:
                snap.y_actual_pos = center
                self._enter(snap, CycleState.RECOVERY_CLAMP_UP)
        elif phase == CycleState.RECOVERY_CLAMP_UP:
            snap.clamp_down, snap.clamp_up = False, True
            if self.phase_elapsed >= 0.4:
                snap.cycle_active = False
                snap.cycle_progress = 0.0
                self._enter(snap, CycleState.IDLE)

    def _return_axes(self, dt: float, snap: MachineSnapshot) -> None:
        ret_vel = self.params["par_x_return_velocity"]
        snap.x_actual_vel = -ret_vel
        snap.x_actual_pos = max(0.0, snap.x_actual_pos - ret_vel * dt)
        center = self.params["par_y_center_pos"]
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
        self.alarm_fired_once = True
        notify_alarms()

    def _clear_demo_alarm(self, snap: MachineSnapshot, alarms, notify_alarms) -> None:
        alarms.clear_active()
        snap.alarm_active = False
        snap.alarm_code = 0
        snap.alarm_count = 0
        snap.vision_heartbeat_ok = True
        snap.start_permitted = True
        snap.cycle_state = int(CycleState.IDLE)
        notify_alarms()
