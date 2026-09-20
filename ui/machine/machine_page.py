"""Screen A — Operatör / Ana Makine ekranı (integration brief section 8-A,
21-22). Default page of the Makine Ekranı."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.cycle_state import cycle_state_label
from core.models import ConnectionState, MachineSnapshot
from persistence.alarms import (
    SEVERITY_ALARM,
    SEVERITY_LABELS_TR,
    SEVERITY_MESSAGE,
    SEVERITY_WARNING,
    AlarmEvent,
)
from services.machine_service import MachineService
from ui.machine.theme import COLORS, base_font
from ui.machine.widgets import ProcessStatusCard, Readout, SectionTabs, StatusChip, touch_button

SEVERITY_ROW_COLOR = {
    SEVERITY_ALARM: COLORS["danger"],
    SEVERITY_WARNING: COLORS["warning"],
    SEVERITY_MESSAGE: COLORS["brand_cyan"],
}


def filter_alarm_events(
    events: list[AlarmEvent], selected_severities: set[str]
) -> list[AlarmEvent]:
    """Saf, Qt'siz filtre - kullanıcı isteği (2026-09-18): "sadece uyarı /
    sadece mesaj / sadece hata gibi ama defaultda hepsi gözüksün". Herhangi
    bir kombinasyon seçilebilir; boş seçim boş liste döndürür (hiçbiri
    işaretli değilse hiçbir satır gösterilmez)."""
    return [e for e in events if e.severity in selected_severities]

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


def compute_start_inhibit_reasons(
    snap: MachineSnapshot, x_start_pos: float, y_center_pos: float
) -> list[str]:
    """H3 (2026-09-18, kullanıcı test notu): "eksik olan koşul açık şekilde
    bildirilmelidir" - StartPermitted=FALSE iken PLC'nin zaten yayınladığı
    alt bileşenlerden (MachineReady'yi oluşturan servo/vision/emergency,
    ayrıca xX_AtStart/xY_AtCenter) bir açıklama üretir. PLC'nin kendi
    `xStartPermitted` formülünü (MachineReady AND NOT xManualMode AND NOT
    xCycleActive AND xX_AtStart AND xY_AtCenter) YENİDEN HESAPLAMAZ/ikame
    etmez - Start butonu hâlâ tek başına `snap.start_permitted`'e bakar; bu
    liste salt bilgilendirmedir, arıza/alarm mesajından ayrıdır.

    Bilinen sınırlama: fiziksel/HMI Stop butonunun "şu an basılı" durumu
    için ayrı, gerçek bir PLC tagı yayınlanmıyor - bu nedenle "Stop basılı"
    nedeni burada YOKTUR (bulunmayan tag için tahmin yapılmaz, görev notu).
    """
    if snap.start_permitted or snap.stale:
        return []
    if snap.manual_mode:
        return ["Manuel modda — Start otomatik modda kullanılır."]
    if snap.cycle_active:
        return ["Çevrim zaten aktif."]

    reasons: list[str] = []
    if snap.emergency_active:
        reasons.append("Acil durdurma aktif.")
    if not snap.x_servo_ready:
        reasons.append("X servo hazır değil.")
    if not snap.y_servo_ready:
        reasons.append("Y servo hazır değil.")
    if not (snap.vision_ready and snap.vision_heartbeat_ok and not snap.vision_fault):
        reasons.append("Vision hazır değil.")
    if not snap.x_at_start:
        reasons.append(f"X başlangıç konumunda değil (ayarlı: {x_start_pos:g} mm).")
    if not snap.y_at_center:
        reasons.append(f"Y merkez konumunda değil (ayarlı: {y_center_pos:g} mm).")
    if not reasons:
        # PLC'nin gördüğümüz tüm alt bileşenleri TRUE görünüyor ama
        # MachineReady/StartPermitted hâlâ FALSE - HMI'nin görmediği bir
        # PLC-içi koşul var; bunu KESİN bir neden gibi sunmuyoruz.
        reasons.append("Makine hazır değil (bilinen koşulların dışında bir PLC koşulu olabilir).")
    return reasons


class MachinePage(QWidget):
    navigateRequested = Signal(str)  # "manual" | "settings" | "alarms" | "camera"

    def __init__(self, service: MachineService, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = service
        self._build_ui()

        service.snapshotUpdated.connect(self._on_snapshot)
        service.connectionStateChanged.connect(self._on_connection_state)
        service.alarmsChanged.connect(self._refresh_alarm_table)
        self._refresh_alarm_table()

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

        # H3 (2026-09-18): StartPermitted=FALSE nedenini operatöre açıklar.
        self._start_inhibit_label = QLabel("")
        self._start_inhibit_label.setWordWrap(True)
        self._start_inhibit_label.setStyleSheet(f"color: {COLORS['warning']};")
        self._start_inhibit_label.setVisible(False)
        root.addWidget(self._start_inhibit_label)

        root.addWidget(self._build_alarm_panel())

        root.addStretch(1)

        # CNC kontrolcülerinde alışıldığı gibi sayfa geçiş sekmeleri ekranın
        # en altına sabitlenir; boşluk üstteki stretch'e gider.
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
        bar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
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

    def _build_alarm_panel(self) -> QFrame:
        """Alarm/Uyarı/Mesaj panosu (kullanıcı isteği, 2026-09-18): H4'ün
        (merkezi alarm ekranı) PLC C2 sözleşmesini beklemeyen kısmı - ekran
        ve veri modeli. Canlı PLC alarm tagı bağlanmadı; satırlar şimdilik
        elle/başka yollarla doldurulacak ("onları dolduracağız")."""
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        filter_row = QHBoxLayout()
        filter_label = QLabel("Göster:")
        filter_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        filter_row.addWidget(filter_label)
        self._alarm_filter_checks: dict[str, QCheckBox] = {}
        for severity in (SEVERITY_ALARM, SEVERITY_WARNING, SEVERITY_MESSAGE):
            cb = QCheckBox(SEVERITY_LABELS_TR[severity])
            cb.setChecked(True)  # varsayılan: hepsi görünür
            cb.toggled.connect(self._refresh_alarm_table)
            self._alarm_filter_checks[severity] = cb
            filter_row.addWidget(cb)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        self._alarm_table = QTableWidget(0, 4)
        self._alarm_table.setHorizontalHeaderLabels(["Saat", "Tür", "Kaynak", "Mesaj"])
        self._alarm_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._alarm_table.verticalHeader().setVisible(False)
        self._alarm_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._alarm_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._alarm_table.setMaximumHeight(150)
        layout.addWidget(self._alarm_table)
        return frame

    def _refresh_alarm_table(self) -> None:
        # Kullanıcı isteği (2026-09-18): "resetle temizlendiyse ana ekrandan
        # gitmeli" - ana ekran panosu yalnız AKTİF (cleared_at yok) satırları
        # gösterir; geçmiş/temizlenmiş kayıtlar ALARMLAR sayfasının "Geçmiş
        # Alarmlar" sekmesine ait.
        active_events = [e for e in self._service.recent_alarms() if e.active]
        selected = {sev for sev, cb in self._alarm_filter_checks.items() if cb.isChecked()}
        events = filter_alarm_events(active_events, selected)
        table = self._alarm_table
        table.setRowCount(len(events))
        for row, event in enumerate(events):
            values = [
                event.occurred_at.strftime("%H:%M:%S"),
                SEVERITY_LABELS_TR.get(event.severity, event.severity),
                event.source,
                event.message,
            ]
            color = SEVERITY_ROW_COLOR.get(event.severity, COLORS["text_primary"])
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 1:
                    item.setForeground(QColor(color))
                table.setItem(row, col, item)

    # -- data binding ---------------------------------------------------------

    def _on_connection_state(self, state: str) -> None:
        self._plc_chip.set_state(CONNECTION_CHIP_STATE.get(state, "fault"), CONNECTION_CHIP_TEXT.get(state, state))

    def _on_snapshot(self, snap: MachineSnapshot) -> None:
        stale = snap.stale

        self._x_readout.set_value("--" if stale else f"{snap.x_actual_pos:.1f}")
        self._y_readout.set_value("--" if stale else f"{snap.y_actual_pos:+.2f}")
        self._cycle_readout.set_value(cycle_state_label(snap.cycle_state) if not stale else "--")

        self._progress.setValue(0 if stale else int(round(snap.cycle_progress)))

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
        # H1 (2026-09-18, kullanıcı test notu): "Manuel Aktif" ifadesi,
        # üstteki ÇEVRİM DURUMU kartının "Manuel" (eMachineState=MANUAL)
        # göstergesiyle aynı ekranda karışıklık yaratıyordu. "Operatör
        # Kontrolü" olarak değiştirildi - kilitli görünüm aynı. PLC'nin
        # kendi `FeedManualAllowed` hesabına güveniliyor (GVL notu: "Auto
        # çevrimde FALSE olacak") - `cycle_active` ile ayrıca ikinci kez
        # kapatılmıyor, bu MANUAL modda VEYA cycle_active öncesi (WAIT_FOR_
        # MATERIAL) izinli olabilmesini engelliyordu.
        self._feed_card.set_status(
            "OPERATÖR KONTROLÜ" if snap.feed_manual_allowed else "KİLİTLİ",
            "ok" if snap.feed_manual_allowed else "inactive",
        )

        self._start_btn.setEnabled(snap.start_permitted and not stale)

        reasons = compute_start_inhibit_reasons(
            snap,
            self._service.get_parameter_value("lr_x_cut_start_pos"),
            self._service.get_parameter_value("lr_y_center_position"),
        )
        if reasons:
            self._start_inhibit_label.setText("Start engelli: " + " ".join(reasons))
            self._start_inhibit_label.setVisible(True)
        else:
            self._start_inhibit_label.setVisible(False)
