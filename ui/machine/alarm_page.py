"""Alarm screen (integration brief section 9): Saat / Kod / Kaynak / Alarm /
Durum, backed by the local SQLite alarm history so it survives a restart.

2026-09-18 (kullanıcı isteği): iki sekme - "Güncel Alarmlar" (yalnız aktif/
temizlenmemiş kayıtlar) ve "Geçmiş Alarmlar" (tüm kayıtlar, temizlenmiş
dahil). Önceden tek, karışık bir tabloydu; artık ana ekrandaki panonun
mantığıyla tutarlı: temizlenen bir kayıt "güncel" görünümden çıkar."""

from __future__ import annotations

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

from core.notification_catalog import NOTIFICATION_CATALOG
from persistence.alarms import SEVERITY_ALARM, SEVERITY_LABELS_TR, SEVERITY_MESSAGE, SEVERITY_WARNING
from services.machine_service import MachineService
from ui.machine.theme import COLORS, base_font
from ui.machine.widgets import touch_button

COLUMNS = ["Saat", "Tür", "Kod", "Kaynak", "Alarm", "Durum"]
CATALOG_COLUMNS = ["Kod", "Tür", "Ne Zaman Görünür", "Anlamı / Yapılacak"]

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


def _build_catalog_table() -> QTableWidget:
    """Kullanıcı isteği (2026-09-22): "Operatör alarm listesine bakıp
    alarmların anlamlarını okuyabilsin... oradan bakıp bize feedback
    verebilir." - CANLI veri değil, `core/notification_catalog.py`'deki
    statik sözlüğün salt-okunur bir görünümü."""
    table = QTableWidget(len(NOTIFICATION_CATALOG), len(CATALOG_COLUMNS))
    table.setHorizontalHeaderLabels(CATALOG_COLUMNS)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    table.setColumnWidth(0, 55)
    table.setColumnWidth(1, 70)
    table.setColumnWidth(2, 190)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setWordWrap(True)
    for row, entry in enumerate(NOTIFICATION_CATALOG):
        values = [
            entry.catalog_id,
            SEVERITY_LABELS_TR.get(entry.severity, entry.severity),
            entry.context,
            entry.text,
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col == 1:
                item.setForeground(QColor(_SEVERITY_ROW_COLOR.get(entry.severity, COLORS["text_primary"])))
            table.setItem(row, col, item)
    table.resizeRowsToContents()
    return table


class AlarmPage(QWidget):
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
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(reset_btn)
        root.addLayout(header)

        # PLC-HMI-20260922-18 (HMI-A04, C06_1 audit): "eksik eşlemeler için
        # görünür eksik/bilinmiyor açıklaması ver" - hangi H/U kodlarının
        # gerçek config'te henüz bir NodeId'si olmadığını (bu yüzden hiç
        # tetiklenemeyeceğini), config'ten CANLI okuyarak gösterir. Statik
        # bir metin değil - PLC online doğrulayıp gerçek config'e eklenince
        # otomatik kaybolur.
        self._pending_tags_label = QLabel()
        self._pending_tags_label.setWordWrap(True)
        self._pending_tags_label.setStyleSheet(f"color: {COLORS['warning']};")
        self._pending_tags_label.setVisible(False)
        root.addWidget(self._pending_tags_label)

        self._tabs = QTabWidget()
        self._current_table = _build_alarm_table()
        self._history_table = _build_alarm_table()
        self._tabs.addTab(self._current_table, "Güncel Alarmlar")
        self._tabs.addTab(self._history_table, "Geçmiş Alarmlar")
        # Kullanıcı isteği (2026-09-22): operatörün her bildirimin anlamını
        # okuyabileceği statik bir referans - canlı veri değil, tek seferlik
        # doldurulur (`core/notification_catalog.py`).
        self._tabs.addTab(_build_catalog_table(), "Alarm Listesi")
        root.addWidget(self._tabs, stretch=1)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._refresh()
        self._refresh_pending_tags()

    def _refresh_pending_tags(self) -> None:
        pending = self._service.pending_candidate_catalog_ids()
        if pending:
            self._pending_tags_label.setText(
                "Online doğrulama bekleyen kodlar (gerçek config'te tag eşlemesi "
                "yok, bu yüzden hiç tetiklenmez): " + ", ".join(pending)
            )
            self._pending_tags_label.setVisible(True)
        else:
            self._pending_tags_label.setVisible(False)

    def _refresh(self) -> None:
        # PLC-HMI-20260922-18 (HMI-A02): "Güncel Alarmlar" `active_alarms()`
        # kullanır (SINIRSIZ) - `recent_alarms()` (Geçmiş Alarmlar için,
        # bilinçli olarak son 100 ile sınırlı) filtrelenirse, 100'den fazla
        # geçmiş kayıt birikince gerçekten aktif eski bir HATA gizlenebilirdi.
        _fill_alarm_table(self._current_table, self._service.active_alarms())
        _fill_alarm_table(self._history_table, self._service.recent_alarms())
