"""Single, central machine service (brief section 26: "Her sayfada ayrı OPC
UA client oluşturma; tek merkezi service kullan"). Every UI page talks to
this service only — never to `plc.opcua_client` directly.

Owns:
- the OPC UA worker thread when a real endpoint is configured,
- the demo/simulation fallback when it is not (`config/opcua.json` empty
  endpoint => Demo mode, brief acceptance criterion #9),
- the shared MachineSnapshot cache, refreshed to the UI on a fixed timer
  (brief section 20: PLC/vision acquisition can be fast, the operator
  screen only needs 10-20 FPS),
- alarm history and engineering parameter persistence.

UI is never the source of truth: it only requests commands and displays
whatever this service reports (brief section 32).
"""

from __future__ import annotations

import logging
import time

from PySide6.QtCore import QObject, QTimer, Signal

from core.cycle_state import AUTO_CYCLE_ACTIVE_STATES, CycleState
from core.models import ConnectionState, MachineSnapshot
from core.parameters import PARAMETER_SPECS
from persistence.alarms import AlarmEvent, AlarmRepository
from persistence.settings_store import SettingsStore
from plc.opcua_client import OpcUaWorker
from plc.tag_map import TagMap, load_config, save_config

logger = logging.getLogger(__name__)

UI_TICK_MS = 50


class MachineService(QObject):
    snapshotUpdated = Signal(MachineSnapshot)
    connectionStateChanged = Signal(str)
    alarmsChanged = Signal()

    def __init__(self, config_path=None, parent=None):
        super().__init__(parent)
        self._config_path = config_path
        self._config = load_config(config_path)
        self._tag_map = TagMap(self._config)
        self._snapshot = MachineSnapshot()
        self._alarms = AlarmRepository()
        self._settings_store = SettingsStore()
        self._worker: OpcUaWorker | None = None

        self.demo_mode = not self._config.is_configured

        stored_params = self._settings_store.get_all()
        self._param_cache: dict[str, float] = {
            spec.key: float(stored_params.get(spec.key, spec.default)) for spec in PARAMETER_SPECS
        }

        from services.demo_simulator import DemoSimulator

        self._demo: DemoSimulator | None = DemoSimulator() if self.demo_mode else None
        if self._demo is not None:
            self._demo.params.update(self._param_cache)
            self._demo.apply_initial(self._snapshot)

        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._on_tick)

    # -- lifecycle --------------------------------------------------------

    def start(self) -> None:
        if self.demo_mode:
            self._snapshot.connection_state = ConnectionState.DEMO
            self._snapshot.stale = False
            self.connectionStateChanged.emit(ConnectionState.DEMO)
        else:
            self._worker = OpcUaWorker(self._config, self._tag_map)
            self._worker.snapshotReady.connect(self._on_raw_snapshot)
            self._worker.connectionStateChanged.connect(self._on_connection_state)
            self._worker.errorOccurred.connect(self._on_error)
            self._worker.start()
        self._ui_timer.start(UI_TICK_MS)

    def shutdown(self) -> None:
        self._ui_timer.stop()
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(2000)

    @property
    def snapshot(self) -> MachineSnapshot:
        return self._snapshot

    @property
    def endpoint(self) -> str:
        return self._config.endpoint

    # -- PLC state ingestion (real mode) -----------------------------------

    def _on_connection_state(self, state: str) -> None:
        self._snapshot.connection_state = state
        self.connectionStateChanged.emit(state)

    def _on_error(self, message: str) -> None:
        logger.warning("PLC error: %s", message)

    def _on_raw_snapshot(self, raw: dict) -> None:
        snap = self._snapshot
        snap.timestamp = time.monotonic()
        snap.stale = False

        def b(name: str, default: bool) -> bool:
            v = raw.get(name)
            return bool(v) if v is not None else default

        def f(name: str, default: float) -> float:
            v = raw.get(name)
            return float(v) if v is not None else default

        def i(name: str, default: int) -> int:
            v = raw.get(name)
            return int(v) if v is not None else default

        snap.machine_ready = b("machine_ready", snap.machine_ready)
        snap.auto_mode = b("auto_mode", snap.auto_mode)
        snap.manual_mode = b("manual_mode", snap.manual_mode)
        snap.cycle_active = b("cycle_active", snap.cycle_active)
        snap.cycle_state = i("cycle_state", snap.cycle_state)
        snap.cycle_progress = f("cycle_progress", snap.cycle_progress)
        snap.start_permitted = b("start_permitted", snap.start_permitted)
        snap.estop_ok = b("estop_ok", snap.estop_ok)
        snap.safety_ok = b("safety_ok", snap.safety_ok)
        snap.x_servo_ready = b("x_servo_ready", snap.x_servo_ready)
        snap.x_fault = b("x_fault", snap.x_fault)
        snap.x_fault_code = i("x_fault_code", snap.x_fault_code)
        snap.x_actual_pos = f("x_actual_pos", snap.x_actual_pos)
        snap.x_actual_vel = f("x_actual_vel", snap.x_actual_vel)
        snap.y_servo_ready = b("y_servo_ready", snap.y_servo_ready)
        snap.y_fault = b("y_fault", snap.y_fault)
        snap.y_fault_code = i("y_fault_code", snap.y_fault_code)
        snap.y_actual_pos = f("y_actual_pos", snap.y_actual_pos)
        snap.y_set_pos = f("y_set_pos", snap.y_set_pos)
        snap.y_set_vel = f("y_set_vel", snap.y_set_vel)
        snap.clamp_down = b("clamp_down", snap.clamp_down)
        snap.clamp_up = b("clamp_up", snap.clamp_up)
        snap.blade_down = b("blade_down", snap.blade_down)
        snap.blade_up = b("blade_up", snap.blade_up)
        snap.feed_forward_input = b("feed_forward_input", snap.feed_forward_input)
        snap.feed_reverse_input = b("feed_reverse_input", snap.feed_reverse_input)
        snap.feed_running = b("feed_running", snap.feed_running)
        snap.feed_manual_allowed = b("feed_manual_allowed", snap.feed_manual_allowed)
        snap.vision_ready = b("vision_ready", snap.vision_ready)
        snap.line_valid = b("line_valid", snap.line_valid)
        snap.vision_fault = b("vision_fault", snap.vision_fault)
        snap.vision_heartbeat_ok = b("vision_heartbeat_ok", snap.vision_heartbeat_ok)
        snap.vision_target_x = f("vision_target_x", snap.vision_target_x)
        snap.vision_target_y = f("vision_target_y", snap.vision_target_y)
        snap.vision_confidence = f("vision_confidence", snap.vision_confidence)
        snap.vision_slope = f("vision_slope", snap.vision_slope)
        snap.alarm_active = b("alarm_active", snap.alarm_active)
        snap.alarm_code = i("alarm_code", snap.alarm_code)
        snap.alarm_count = i("alarm_count", snap.alarm_count)

        for spec in PARAMETER_SPECS:
            if spec.key in raw:
                self._param_cache[spec.key] = float(raw[spec.key])

    def _on_tick(self) -> None:
        if self.demo_mode and self._demo is not None:
            self._demo.tick(UI_TICK_MS / 1000.0, self._snapshot, self._alarms, self.alarmsChanged.emit)
        else:
            age_ms = (time.monotonic() - self._snapshot.timestamp) * 1000
            self._snapshot.stale = age_ms > self._config.stale_timeout_ms
        self.snapshotUpdated.emit(self._snapshot)

    # -- commands (called from the UI thread) ------------------------------

    def _manual_allowed(self) -> bool:
        try:
            state = CycleState(self._snapshot.cycle_state)
        except ValueError:
            return self._snapshot.manual_mode
        return self._snapshot.manual_mode and state not in AUTO_CYCLE_ACTIVE_STATES

    def request_start(self) -> None:
        if self.demo_mode and self._demo is not None:
            self._demo.request_start()
        elif self._worker is not None:
            self._worker.request_pulse("cmd_start")

    def request_stop(self) -> None:
        if self.demo_mode and self._demo is not None:
            self._demo.request_stop()
        elif self._worker is not None:
            self._worker.request_pulse("cmd_stop")

    def request_reset(self) -> None:
        if self.demo_mode and self._demo is not None:
            self._demo.request_reset()
            return
        if self._worker is not None:
            self._worker.request_pulse("cmd_reset")
        self._alarms.clear_active()
        self.alarmsChanged.emit()

    def set_auto_mode(self, auto: bool) -> None:
        if self.demo_mode and self._demo is not None:
            self._demo.set_mode(auto)
        elif self._worker is not None:
            self._worker.request_pulse("cmd_auto_mode" if auto else "cmd_manual_mode")

    def jog_x(self, direction: int, active: bool, fast: bool = False) -> None:
        if active and not self._manual_allowed():
            return
        if self.demo_mode and self._demo is not None:
            self._demo.set_jog_x(direction, active, fast)
        elif self._worker is not None:
            # NOTE (brief section 28, open point): no PLC tag for jog speed
            # select is defined yet; both speeds currently map to the same
            # HMI_CmdXJog* tag until a fast/slow contract is agreed.
            tag = "cmd_x_jog_plus" if direction > 0 else "cmd_x_jog_minus"
            self._worker.request_write(tag, active)

    def jog_y(self, direction: int, active: bool, fast: bool = False) -> None:
        if active and not self._manual_allowed():
            return
        if self.demo_mode and self._demo is not None:
            self._demo.set_jog_y(direction, active, fast)
        elif self._worker is not None:
            tag = "cmd_y_jog_plus" if direction > 0 else "cmd_y_jog_minus"
            self._worker.request_write(tag, active)

    def y_center(self) -> None:
        if not self._manual_allowed():
            return
        if self.demo_mode and self._demo is not None:
            self._demo.request_y_center()
        elif self._worker is not None:
            self._worker.request_pulse("cmd_y_center")

    def set_blade(self, down: bool, active: bool) -> None:
        if active and not self._manual_allowed():
            return
        if self.demo_mode and self._demo is not None:
            self._demo.set_blade(down, active)
        elif self._worker is not None:
            tag = "cmd_blade_down" if down else "cmd_blade_up"
            self._worker.request_write(tag, active)

    def set_clamp(self, down: bool, active: bool) -> None:
        if active and not self._manual_allowed():
            return
        if self.demo_mode and self._demo is not None:
            self._demo.set_clamp(down, active)
        elif self._worker is not None:
            tag = "cmd_clamp_down" if down else "cmd_clamp_up"
            self._worker.request_write(tag, active)

    # -- engineering parameters ---------------------------------------------

    def get_parameter_value(self, key: str) -> float:
        return self._param_cache.get(key, 0.0)

    def set_parameter(self, key: str, value: float) -> None:
        spec = next((s for s in PARAMETER_SPECS if s.key == key), None)
        if spec is None:
            raise ValueError(f"Bilinmeyen parametre: {key}")
        if not (spec.min_value <= value <= spec.max_value):
            raise ValueError(
                f"{spec.label_tr} aralık dışı ({spec.min_value:g}-{spec.max_value:g} {spec.unit})"
            )
        self._settings_store.set(key, str(value))
        self._param_cache[key] = value
        if self.demo_mode and self._demo is not None:
            self._demo.params[key] = value
        elif self._worker is not None:
            self._worker.request_write(key, value)

    def update_endpoint(self, endpoint: str) -> None:
        """Persists a new OPC UA endpoint to config; takes effect on restart."""
        self._config.endpoint = endpoint
        save_config(self._config, self._config_path)

    # -- alarms --------------------------------------------------------------

    def recent_alarms(self) -> list[AlarmEvent]:
        return self._alarms.recent()
