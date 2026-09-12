"""Alarm screen (integration brief section 9): Saat / Kod / Kaynak / Alarm /
Durum, backed by the local SQLite alarm history so it survives a restart."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from services.machine_service import MachineService
from ui.machine.theme import COLORS, base_font
from ui.machine.widgets import touch_button

COLUMNS = ["Saat", "Kod", "Kaynak", "Alarm", "Durum"]


class AlarmPage(QWidget):
    navigateRequested = Signal(str)  # "machine_main"

    def __init__(self, service: MachineService, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = service
        self._build_ui()
        service.alarmsChanged.connect(self._refresh)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("ALARMLAR")
        title.setFont(base_font(14, bold=True))
        reset_btn = touch_button("RESET", object_name="resetButton")
        reset_btn.clicked.connect(self._service.request_reset)
        back_btn = touch_button("◀ ANA EKRAN", object_name="navButton")
        back_btn.clicked.connect(lambda: self.navigateRequested.emit("machine_main"))
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(reset_btn)
        header.addWidget(back_btn)
        root.addLayout(header)

        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        root.addWidget(self._table, stretch=1)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        events = self._service.recent_alarms()
        self._table.setRowCount(len(events))
        for row, event in enumerate(events):
            status_text = "AKTİF" if event.active else "TEMİZLENDİ"
            status_color = COLORS["danger"] if event.active else COLORS["success"]
            values = [
                event.occurred_at.strftime("%H:%M:%S"),
                str(event.code),
                event.source,
                event.message,
                status_text,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 4:
                    item.setForeground(QColor(status_color))
                self._table.setItem(row, col, item)
