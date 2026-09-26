"""Small reusable widget set for the Makine Ekranı pages.

We do not have access to VisionCut's real `Card`/`Readout`/`SectionTabs`/
`TouchKeypad` components (brief section 2), so this module defines a minimal
equivalent set, styled with the shared theme tokens, used consistently across
all four screens. If the receiving company already has these components,
this module is the one to delete/replace during integration (see
INTEGRATION.md).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.models import ConnectionState, MachineSnapshot
from ui.machine.theme import COLORS, MIN_TOUCH_HEIGHT, PRIMARY_ACTION_HEIGHT, base_font, tabular_font


def restyle(widget: QWidget, sheet: str) -> None:
    """setStyleSheet, yalnız stil gerçekten değiştiyse.

    Qt her çağrıda - aynı metin olsa bile - widget'ı yeniden stillendirir ve
    çizer. Durum kartları her PLC snapshot'ında (10 Hz) rengini yeniden
    yazıyordu: 2026-09-26 ölçümü, Demo'da 15 s'de 5655 çağrı; süreç tek
    çekirdeğin %78'ini kullanıyordu. IPC'de aynı işlemciyi kesim sırasında
    VisionCut'ın görüntü işlemesiyle paylaşıyor.
    """
    if widget.styleSheet() != sheet:
        widget.setStyleSheet(sheet)


class Card(QFrame):
    """A titled panel with a dark navy surface, per the VisionCut palette."""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 10, 14, 10)
        self._layout.setSpacing(6)

        self._title_label: QLabel | None = None
        if title:
            self._title_label = QLabel(title.upper())
            self._title_label.setFont(base_font(10, bold=True))
            self._title_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            self._layout.addWidget(self._title_label)

    def body_layout(self) -> QVBoxLayout:
        return self._layout


class Readout(Card):
    """Card showing one large numeric/text value with a title above it."""

    def __init__(self, title: str, initial: str = "--", unit: str = "", parent: QWidget | None = None):
        super().__init__(title, parent)
        self._value_label = QLabel(initial)
        self._value_label.setFont(tabular_font(26, bold=True))
        self._value_label.setStyleSheet(f"color: {COLORS['text_primary']};")

        if unit:
            row = QHBoxLayout()
            row.addWidget(self._value_label)
            unit_label = QLabel(unit)
            unit_label.setFont(base_font(12))
            unit_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            unit_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
            row.addWidget(unit_label)
            row.addStretch(1)
            self.body_layout().addLayout(row)
        else:
            self.body_layout().addWidget(self._value_label)

    def set_value(self, text: str) -> None:
        self._value_label.setText(text)

    def set_color(self, color_hex: str) -> None:
        restyle(self._value_label, f"color: {color_hex};")


class StatusChip(QFrame):
    """Small pill used in the top status bar (PLC/Vision/Servo/Mode/Alarm)."""

    STATE_COLORS = {
        "ok": COLORS["success"],
        "warn": COLORS["warning"],
        "fault": COLORS["danger"],
        "inactive": COLORS["text_muted"],
    }

    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        self._dot = QLabel("●")
        self._text = QLabel(label)
        self._text.setFont(base_font(10, bold=True))
        layout.addWidget(self._dot)
        layout.addWidget(self._text)

        self.set_state("inactive", label)

    def set_state(self, state: str, text: str | None = None) -> None:
        color = self.STATE_COLORS.get(state, COLORS["text_muted"])
        restyle(self._dot, f"color: {color}; font-size: 12px;")
        if text is not None:
            self._text.setText(text)
        restyle(
            self,
            f"QFrame {{ background-color: {COLORS['navy']}; border: 1px solid {COLORS['border']};"
            f" border-radius: 14px; }}"
        )


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


class MachineStatusBar(QFrame):
    """Üst özet çubuğu (PLC/Vision/Servo/Mod/Alarm) - kullanıcı isteği
    (2026-09-23): önceden yalnız `MachinePage`e özeldi, artık `MainWindow`
    tarafından TEK bir örnek olarak üstte sabitlenip her sayfada (Ayarlar,
    Manuel, Alarmlar, Kamera dahil) aynı şekilde görünür - kendi servis
    sinyallerine doğrudan abone olur, sayfa değişiminden etkilenmez."""

    def __init__(self, service, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = service
        self.setObjectName("statusBar")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
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

        service.snapshotUpdated.connect(self._on_snapshot)
        service.connectionStateChanged.connect(self._on_connection_state)

    def _on_connection_state(self, state: str) -> None:
        self._plc_chip.set_state(CONNECTION_CHIP_STATE.get(state, "fault"), CONNECTION_CHIP_TEXT.get(state, state))

    def _on_snapshot(self, snap: MachineSnapshot) -> None:
        vision_ok = snap.vision_ready and snap.vision_heartbeat_ok and not snap.vision_fault
        if snap.vision_fault:
            vision_state, vision_text = "fault", "VISION: HATA"
        elif not snap.vision_heartbeat_ok:
            vision_state, vision_text = "fault", "VISION: YANIT YOK"
        elif vision_ok:
            vision_state, vision_text = "ok", "VISION: HAZIR"
        else:
            vision_state, vision_text = "inactive", "VISION: --"
        self._vision_chip.set_state(vision_state, vision_text)
        self._x_servo_chip.set_state(
            "fault" if snap.x_fault else ("ok" if snap.x_servo_ready else "inactive"),
            "X SERVO: HATA" if snap.x_fault else ("X SERVO: HAZIR" if snap.x_servo_ready else "X SERVO: --"),
        )
        self._y_servo_chip.set_state(
            "fault" if snap.y_fault else ("ok" if snap.y_servo_ready else "inactive"),
            "Y SERVO: HATA" if snap.y_fault else ("Y SERVO: HAZIR" if snap.y_servo_ready else "Y SERVO: --"),
        )
        self._mode_chip.set_state("ok" if snap.auto_mode else "warn", "MOD: AUTO" if snap.auto_mode else "MOD: MANUEL")
        alarm_count = self._service.active_alarm_count()
        self._alarm_chip.set_state("fault" if alarm_count > 0 else "ok", f"ALARM: {alarm_count}")


class ProcessStatusCard(Card):
    """Card for a two-state process indicator (e.g. Bıçak: Aşağı/Yukarı)."""

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(title, parent)
        self._label = QLabel("--")
        self._label.setFont(base_font(14, bold=True))
        self.body_layout().addWidget(self._label)

    def set_status(self, text: str, state: str) -> None:
        color = StatusChip.STATE_COLORS.get(state, COLORS["text_muted"])
        self._label.setText(text)
        restyle(self._label, f"color: {color};")


def touch_button(
    text: str,
    object_name: str = "",
    primary: bool = False,
    checkable: bool = False,
) -> QPushButton:
    button = QPushButton(text)
    if object_name:
        button.setObjectName(object_name)
    button.setMinimumHeight(PRIMARY_ACTION_HEIGHT if primary else MIN_TOUCH_HEIGHT)
    button.setCheckable(checkable)
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return button


class HoldButton(QPushButton):
    """A momentary button: emits held(True) on press, held(False) on release
    or when the mouse leaves while pressed. Used for jog / blade / clamp
    controls (brief section 8: momentary manual buttons)."""

    held = Signal(bool)

    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setMinimumHeight(PRIMARY_ACTION_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().mousePressEvent(event)
        if self.isEnabled():
            self.held.emit(True)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().mouseReleaseEvent(event)
        self.held.emit(False)

    def leaveEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().leaveEvent(event)
        if self.isDown():
            self.held.emit(False)


class SectionTabs(QWidget):
    """Alt gezinme satırı (kullanıcı isteği, 2026-09-23): artık her sayfada
    aynı, TEK bir örnek olarak `MainWindow` tarafından sabitlenir (ANA SAYFA
    / Manuel / Ayarlar / Alarmlar / Kamera Ekranı) - hangi sayfada
    olunduğunu görmek için tıklanan sekme işaretli (checked) kalır."""

    tabClicked = Signal(str)

    def __init__(self, items: list[tuple[str, str]], parent: QWidget | None = None):
        """`items` is a list of (key, label)."""
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._buttons: dict[str, QPushButton] = {}
        for key, label in items:
            btn = touch_button(label, object_name="navButton", checkable=True)
            btn.clicked.connect(lambda _checked=False, k=key: self.tabClicked.emit(k))
            layout.addWidget(btn)
            self._buttons[key] = btn

    def button(self, key: str) -> QPushButton:
        return self._buttons[key]

    def set_active(self, key: str) -> None:
        for btn_key, btn in self._buttons.items():
            btn.setChecked(btn_key == key)
