"""Screen A — Operatör / Ana Makine ekranı (integration brief section 8-A,
21-22). Default page of the Makine Ekranı."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from core.cycle_state import cycle_state_label
from core.models import ConnectionState, MachineSnapshot
from services.machine_service import MachineService
from ui.machine.theme import COLORS, base_font
from ui.machine.widgets import ProcessStatusCard, Readout, SectionTabs, StatusChip, touch_button

CONNECTION_CHIP_TEXT = {
    ConnectionState.DISCONNECTED: "PLC: BAĞLI DEĞİL",
    ConnectionState.CONNECTING: "PLC: BAĞLANIYOR",
    ConnectionState.CONNECTED: "PLC: BAĞLI",
    ConnectionState.DEGRADED: "PLC: ZAYIF",
    ConnectionState.ERROR: "PLC: HATA",
    ConnectionState.DEMO: "PLC: DEMO MOD",
}

CONNECTION_CHIP_STATE = {
    ConnectionState.DISCONNECTED: "fault",
    ConnectionState.CONNECTING: "warn",
    ConnectionState.CONNECTED: "ok",
    ConnectionState.DEGRADED: "warn",
    ConnectionState.ERROR: "fault",
    ConnectionState.DEMO: "warn",
}


class MachinePage(QWidget):
    navigateRequested = Signal(str)  # "manual" | "settings" | "alarms" | "camera"

    def __init__(self, service: MachineService, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = service
        self._build_ui()

        service.snapshotUpdated.connect(self._on_snapshot)
        service.connectionStateChanged.connect(self._on_connection_state)

    # -- layout -------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 12)
        root.setSpacing(10)

        root.addWidget(self._build_status_bar())

        readout_row = QHBoxLayout()
        readout_row.setSpacing(10)
        self._x_readout = Readout("X Pozisyonu", "0.0", "mm")
        self._y_readout = Readout("Y Pozisyonu", "+0.00", "mm")
        self._cycle_readout = Readout("Çevrim Durumu", "--")
        readout_row.addWidget(self._x_readout)
        readout_row.addWidget(self._y_readout)
        readout_row.addWidget(self._cycle_readout)
        root.addLayout(readout_row)

        progress_label = QLabel("Kesim İlerlemesi")
        progress_label.setFont(base_font(10, bold=True))
        progress_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        root.addWidget(progress_label)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setTextVisible(True)
        self._progress.setFormat("%p %")
        self._progress.setMinimumHeight(28)
        root.addWidget(self._progress)

        process_row = QHBoxLayout()
        process_row.setSpacing(10)
        self._clamp_card = ProcessStatusCard("Perde Baskısı")
        self._blade_card = ProcessStatusCard("Bıçak")
        self._vision_card = ProcessStatusCard("Vision Çizgi")
        self._feed_card = ProcessStatusCard("Perde Besleme")
        for card in (self._clamp_card, self._blade_card, self._vision_card, self._feed_card):
            process_row.addWidget(card)
        root.addLayout(process_row)

        command_row = QHBoxLayout()
        command_row.setSpacing(10)
        self._start_btn = touch_button("START", object_name="startButton", primary=True)
        self._stop_btn = touch_button("STOP", object_name="stopButton", primary=True)
        self._reset_btn = touch_button("RESET", object_name="resetButton", primary=True)
        self._start_btn.clicked.connect(self._service.request_start)
        self._stop_btn.clicked.connect(self._service.request_stop)
        self._reset_btn.clicked.connect(self._service.request_reset)
        command_row.addWidget(self._start_btn)
        command_row.addWidget(self._stop_btn)
        command_row.addWidget(self._reset_btn)
        root.addLayout(command_row)

        self._nav = SectionTabs(
            [
                ("manual", "MANUEL"),
                ("settings", "AYARLAR"),
                ("alarms", "ALARMLAR"),
                ("camera", "KAMERA EKRANI"),
            ]
        )
        self._nav.button("camera").setObjectName("cameraButton")
        self._nav.tabClicked.connect(self.navigateRequested.emit)
        root.addWidget(self._nav)

    def _build_status_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("statusBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        title = QLabel("BUFERA | MAKİNE")
        title.setFont(base_font(12, bold=True))
        layout.addWidget(title)
        layout.addStretch(1)

        self._plc_chip = StatusChip("PLC: --")
        self._vision_chip = StatusChip("VISION: --")
        self._x_servo_chip = StatusChip("X SERVO: --")
        self._y_servo_chip = StatusChip("Y SERVO: --")
        self._mode_chip = StatusChip("MOD: --")
        self._alarm_chip = StatusChip("ALARM: 0")
        for chip in (
            self._plc_chip,
            self._vision_chip,
            self._x_servo_chip,
            self._y_servo_chip,
            self._mode_chip,
            self._alarm_chip,
        ):
            layout.addWidget(chip)
        return bar

    # -- data binding ---------------------------------------------------------

    def _on_connection_state(self, state: str) -> None:
        self._plc_chip.set_state(CONNECTION_CHIP_STATE.get(state, "fault"), CONNECTION_CHIP_TEXT.get(state, state))

    def _on_snapshot(self, snap: MachineSnapshot) -> None:
        stale = snap.stale

        self._x_readout.set_value("--" if stale else f"{snap.x_actual_pos:.1f}")
        self._y_readout.set_value("--" if stale else f"{snap.y_actual_pos:+.2f}")
        self._cycle_readout.set_value(cycle_state_label(snap.cycle_state) if not stale else "--")

        self._progress.setValue(0 if stale else int(round(snap.cycle_progress)))

        self._vision_chip.set_state(
            "ok" if snap.vision_ready and not snap.vision_fault else ("fault" if snap.vision_fault else "inactive"),
            "VISION: HAZIR" if snap.vision_ready and not snap.vision_fault else "VISION: HATA" if snap.vision_fault else "VISION: --",
        )
        self._x_servo_chip.set_state(
            "fault" if snap.x_fault else ("ok" if snap.x_servo_ready else "inactive"),
            "X SERVO: HATA" if snap.x_fault else ("X SERVO: HAZIR" if snap.x_servo_ready else "X SERVO: --"),
        )
        self._y_servo_chip.set_state(
            "fault" if snap.y_fault else ("ok" if snap.y_servo_ready else "inactive"),
            "Y SERVO: HATA" if snap.y_fault else ("Y SERVO: HAZIR" if snap.y_servo_ready else "Y SERVO: --"),
        )
        self._mode_chip.set_state("ok" if snap.auto_mode else "warn", "MOD: AUTO" if snap.auto_mode else "MOD: MANUEL")
        self._alarm_chip.set_state("fault" if snap.alarm_count > 0 else "ok", f"ALARM: {snap.alarm_count}")

        self._clamp_card.set_status(
            "AŞAĞI" if snap.clamp_down else "YUKARI", "warn" if snap.clamp_down else "ok"
        )
        self._blade_card.set_status(
            "AŞAĞI" if snap.blade_down else "YUKARI", "warn" if snap.blade_down else "ok"
        )
        self._vision_card.set_status(
            "GEÇERLİ" if snap.line_valid else "GEÇERSİZ", "ok" if snap.line_valid else "inactive"
        )
        self._feed_card.set_status(
            "MANUEL AKTİF" if snap.feed_manual_allowed and not snap.cycle_active else "KİLİTLİ",
            "ok" if snap.feed_manual_allowed and not snap.cycle_active else "inactive",
        )

        self._start_btn.setEnabled(snap.start_permitted and not stale)
