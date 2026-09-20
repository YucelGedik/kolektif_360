"""Alarm screen (integration brief section 9): Saat / Kod / Kaynak / Alarm /
Durum, backed by the local SQLite alarm history so it survives a restart.

2026-09-18 (kullanıcı isteği): iki sekme - "Güncel Alarmlar" (yalnız aktif/
temizlenmemiş kayıtlar) ve "Geçmiş Alarmlar" (tüm kayıtlar, temizlenmiş
dahil). Önceden tek, karışık bir tabloydu; artık ana ekrandaki panonun
mantığıyla tutarlı: temizlenen bir kayıt "güncel" görünümden çıkar."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from persistence.alarms import SEVERITY_ALARM, SEVERITY_LABELS_TR, SEVERITY_MESSAGE, SEVERITY_WARNING
from services.machine_service import MachineService
from ui.machine.theme import COLORS, base_font
from ui.machine.widgets import touch_button

COLUMNS = ["Saat", "Tür", "Kod", "Kaynak", "Alarm", "Durum"]

_SEVERITY_ROW_COLOR = {
    SEVERITY_ALARM: COLORS["danger"],
    SEVERITY_WARNING: COLORS["warning"],
    SEVERITY_MESSAGE: COLORS["brand_cyan"],
}


def _fill_alarm_table(table: QTableWidget, events: list) -> None:
    table.setRowCount(len(events))
    for row, event in enumerate(events):
        status_text = "AKTİF" if event.active else "TEMİZLENDİ"
        status_color = COLORS["danger"] if event.active else COLORS["success"]
        severity_text = SEVERITY_LABELS_TR.get(event.severity, event.severity)
        values = [
            event.occurred_at.strftime("%H:%M:%S"),
            severity_text,
            str(event.code) if event.code is not None else "--",
            event.source,
            event.message,
            status_text,
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col == 1:
                item.setForeground(QColor(_SEVERITY_ROW_COLOR.get(event.severity, COLORS["text_primary"])))
            if col == 5:
                item.setForeground(QColor(status_color))
            table.setItem(row, col, item)


def _build_alarm_table() -> QTableWidget:
    table = QTableWidget(0, len(COLUMNS))
    table.setHorizontalHeaderLabels(COLUMNS)
    table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    return table


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

        self._tabs = QTabWidget()
        self._current_table = _build_alarm_table()
        self._history_table = _build_alarm_table()
        self._tabs.addTab(self._current_table, "Güncel Alarmlar")
        self._tabs.addTab(self._history_table, "Geçmiş Alarmlar")
        root.addWidget(self._tabs, stretch=1)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        events = self._service.recent_alarms()
        current = [e for e in events if e.active]
        _fill_alarm_table(self._current_table, current)
        _fill_alarm_table(self._history_table, events)
