"""Screen A — Operatör / Ana Makine ekranı (integration brief section 8-A,
21-22). Default page of the Makine Ekranı."""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.cycle_state import CycleState, cycle_state_label
from core.models import MachineSnapshot
from persistence.alarms import (
    SEVERITY_ALARM,
    SEVERITY_LABELS_TR,
    SEVERITY_MESSAGE,
    SEVERITY_WARNING,
    AlarmEvent,
)
from services.machine_service import MachineService
from ui.machine.theme import COLORS, base_font
from ui.machine.widgets import ProcessStatusCard, Readout, touch_button

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


def _manual_preparation_reason(snap: MachineSnapshot) -> str:
    """U04 (PLC-HMI-20260921-16, C6.1): "eksik retract/sensör/konum
    koşullarını belirt" - PLC'nin `xManualPreparationRequired`'ı FALSE'a
    çekme formülünden (Alarm_Control/Logic_Control) türetilmiş, somut/
    kanıtlı bir eksik listesi; jenerik bir "hazırlık gerekiyor" değil."""
    missing: list[str] = []
    if not snap.blade_retract_accepted:
        missing.append("bıçak Yukarı kabulü bekleniyor")
    if not snap.clamp_retract_accepted:
        missing.append("baskı Yukarı kabulü bekleniyor")
    if snap.blade_down:
        missing.append("bıçak hâlâ aşağıda")
    if snap.clamp_down:
        missing.append("baskı hâlâ aşağıda")
    if not snap.x_at_start:
        missing.append("X başlangıç konumunda değil")
    if not snap.y_at_center:
        missing.append("Y merkez konumunda değil")
    if not (snap.x_servo_ready and snap.y_servo_ready):
        missing.append("servo hazır değil")
    if not missing:
        return "Manuel hazırlığı tamamlayın."
    return "Manuel hazırlığı tamamlayın: " + ", ".join(missing) + "."


def compute_start_inhibit_reasons(
    snap: MachineSnapshot, x_start_pos: float, y_center_pos: float
) -> list[str]:
    """H3 (2026-09-18) + C6/U-katalog (PLC-HMI-20260921-15/16, 2026-09-21):
    "eksik olan koşul açık şekilde bildirilmelidir" VE "ilk engelde return
    edip diğerlerini gizleme" - StartPermitted=FALSE iken PLC'nin zaten
    yayınladığı alt bileşenlerden TÜM geçerli UYARI'ları birlikte üretir
    (yalnız ilkini değil). PLC'nin kendi `xStartPermitted` formülünü
    YENİDEN HESAPLAMAZ/ikame etmez - Start butonu hâlâ tek başına
    `snap.start_permitted`'e bakar; bu liste salt bilgilendirmedir.

    Emniyet (H16) ve gerçek servo/motion arızaları (H06/H07 vb.) burada
    TEKRAR gösterilmez - onlar zaten `_update_alarm_conditions`'ın HATA
    kaydı/panosuyla bildiriliyor, aynı nedeni iki yerde ikiletmemek için.

    Bilinen sınırlama: fiziksel/HMI Stop butonunun "şu an basılı" durumu
    için ayrı, gerçek bir PLC tagı yayınlanmıyor - bu nedenle "Stop basılı"
    nedeni burada YOKTUR (bulunmayan tag için tahmin yapılmaz, görev notu).
    """
    # PLC-HMI-20260922-18 (HMI-A03, C06_1 audit): stale kontrolü start_
    # permitted'DEN ÖNCE gelmeli. Eskiden sıra tersti - `snap.start_
    # permitted` bağlantı koptuğunda PLC'den gelen SON (artık bayat) değeri
    # taşımaya devam ediyor; TRUE idiyse fonksiyon erken [] dönüyor ve U10
    # hiç görünmüyordu (repro: stale=True + start_permitted=True -> []).
    if snap.stale:
        # U10: veri güncel değilken izin/konum nedeni UYDURULMAZ, veri
        # eksikliği ayrı bir UYARI olarak açıkça belirtilir. Kod, operatörün
        # bu metni "Alarm Listesi" referans sekmesindeki (core/notification_
        # catalog.py) satırla eşleştirebilmesi için baştaki [Uxx] etiketiyle
        # gösterilir (kullanıcı geri bildirimi, 2026-09-22).
        return ["[U10] PLC verisi güncel değil; izin/konum bilgisi doğrulanamıyor."]
    if snap.start_permitted:
        return []
    if snap.cycle_active:
        # Görev notu: "aktif çevrimde Start uygun değil" normal bir durumdur,
        # alarm yağmuruna çevrilmez - hiç gösterilmez.
        return []

    reasons: list[str] = []
    if not snap.x_at_start:  # U01
        reasons.append(f"[U01] X başlangıç konumunda değil (ayarlı: {x_start_pos:g} mm).")
    if not snap.y_at_center:  # U02
        reasons.append(f"[U02] Y merkez konumunda değil (ayarlı: {y_center_pos:g} mm).")
    if snap.manual_mode:  # U03
        reasons.append("[U03] Start için Otomatik modu seçin.")
    if snap.manual_preparation_required:  # U04
        reasons.append("[U04] " + _manual_preparation_reason(snap))
    # U05 (yalnız bıçak - baskı için EKLENMEDİ, görev notu). PLC-HMI-
    # 20260922-18 (HMI-A06, C06_1 audit) bulgusu: PLC sözleşmesi bu koşulu
    # `BladeZDown OR xBladeValveCmd` olarak tanımlıyor ama `xBladeValveCmd`
    # hiç yayınlanmış/config'e eklenmiş bir HMI tag'i değil - HMI yalnız
    # `BladeZDown` sensörünü (blade_down) görüyor. Görmediğimiz bir valf
    # komutu tahmin EDİLMEZ; genel U11 "PLC Start izni yok" yedeği zaten bu
    # boşluğu dürüstçe kapatıyor (PLC'nin `start_permitted` hesabı kendi
    # xBladeValveCmd bilgisini içerir, HMI onu yeniden üretmez).
    if snap.blade_down:  # U05
        reasons.append("[U05] Start için bıçağı kaldırın.")
    if snap.operator_stop_active:  # U06 - PLC-HMI-20260922-18: export'ta var, online doğrulama bekliyor, hep False
        reasons.append("[U06] Stop talebi aktif; Start engelli.")
    if not snap.x_servo_ready and not snap.x_fault:  # U07 (gerçek arıza H06'da ayrı gösterilir)
        reasons.append("[U07] X servo hazır değil.")
    if not snap.y_servo_ready and not snap.y_fault:  # U07
        reasons.append("[U07] Y servo hazır değil.")
    if not snap.vision_heartbeat_ok:  # U08
        reasons.append("[U08] Vision heartbeat alınmıyor/güncellenmiyor. PLC bağlantısı taze olmalı.")
    if not snap.vision_ready and not snap.vision_fault:  # U09 (gerçek arıza H17'de ayrı)
        reasons.append("[U09] Vision hazır değil.")
    if not reasons:
        # U11: PLC'nin gördüğümüz tüm alt bileşenleri TRUE görünüyor ama
        # StartPermitted hâlâ FALSE - HMI'nin görmediği bir PLC-içi koşul
        # var; bunu KESİN bir neden gibi sunmuyoruz, PLC'nin iznini aşmıyoruz.
        reasons.append("[U11] PLC Start izni yok; ek koşul bilgisi gerekli.")
    return reasons


# PLC-HMI-20260922-18 (HMI-A05, C06_1 audit): görev notundaki eşleme -
# "40 kamera,60 talep,30/70 sensör,90/110 çıkış,130 dönüş,140 durduruluyor,
# 510 manuel hazırlık,500 otomatik Stop devam yolu". M08 burada YOK - tek
# seferlik "yeni sonuç" olduğu için ayrı, geçiş (edge) tabanlı üretilir.
_CYCLE_STATE_MESSAGE_MAP: dict[int, str] = {
    int(CycleState.WAIT_VISION): "[M01] Kamera verisi bekleniyor.",
    int(CycleState.WAIT_BLADE_REQUEST): "[M02] Bıçak talebi / geçerli yörünge bekleniyor.",
    int(CycleState.CLAMP_DOWN): "[M03] Baskı/bıçak aşağı sensörü bekleniyor.",
    int(CycleState.BLADE_DOWN): "[M03] Baskı/bıçak aşağı sensörü bekleniyor.",
    int(CycleState.BLADE_UP): "[M04] Bıçak/baskı aşağı sensöründen çıkış bekleniyor.",
    int(CycleState.CLAMP_UP): "[M04] Bıçak/baskı aşağı sensöründen çıkış bekleniyor.",
    int(CycleState.MANUAL_RETURN): "[M05] Başlangıç konumuna dönülüyor.",
    int(CycleState.MANUAL_RETURN_STOP): "[M06] Dönüş durduruluyor; talepleri bırakın.",
    int(CycleState.RECOVERY): "[M07] Manuel modu seçerek hazırlığı yapın.",
    int(CycleState.STOPPING): "[M09] Otomatik çevrim durduruluyor; mevcut devam yolu bıçak yukarı/eksen dönüşü.",
}


def compute_active_state_message(snap: MachineSnapshot) -> str | None:
    """PLC-HMI-20260922-18 (HMI-A05): "MESAJ" sınıfı hiçbir yere canlı
    yansımıyordu - `core/notification_catalog.py`deki M01-M09 yalnız statik
    referanstı. `snap.cycle_state`'e karşılık gelen SÜREKLİ (o durumda
    kaldığı sürece görünen) mesajı üretir. Bağlantı bayatken kesin bir
    süreç mesajı UYDURULMAZ (görev notu)."""
    if snap.stale:
        return None
    return _CYCLE_STATE_MESSAGE_MAP.get(snap.cycle_state)


class MachinePage(QWidget):
    def __init__(self, service: MachineService, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = service
        # U01-U11 (Start engelleri) - kullanıcı isteği (2026-09-22): "tabloda
        # yazılsın ama banner gibi kalıcı olmasın... resete bağlı değil, şu
        # an hangi mantıkla çalışıyorsa tablonun içinde de o mantıkla
        # çalışsın." AlarmRepository'ye YAZILMAZ (alarm yağmuru hedefi aynen
        # duruyor) - yalnız her snapshot tick'inde canlı hesaplanır/kaybolur,
        # `_refresh_alarm_table`'a `_on_snapshot`'tan aktarılır.
        self._live_warning_messages: list[str] = []
        # PLC-HMI-20260922-18 (HMI-A05): M08 diğer M-kodları gibi "durum
        # sürerken görünen" değil, "yeni sonuç" - yalnız move_to_start_
        # status() İLK KEZ "done" olduğu tick'te bir kez gösterilir (aynı
        # durum sonraki tick'lerde sürse bile tekrar eklenmez).
        self._live_message_texts: list[str] = []
        self._move_to_start_was_done = False
        self._build_ui()

        service.snapshotUpdated.connect(self._on_snapshot)
        service.alarmsChanged.connect(self._refresh_alarm_table)
        self._refresh_alarm_table()

    # -- layout -------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 12)
        root.setSpacing(10)

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
        # Alarmlar" sekmesine ait. PLC-HMI-20260922-18 (HMI-A02): SINIRSIZ
        # `active_alarms()` - `recent_alarms()` (son 100) filtrelenirse eski
        # bir aktif HATA gizlenebilirdi.
        active_events = self._service.active_alarms()
        selected = {sev for sev, cb in self._alarm_filter_checks.items() if cb.isChecked()}
        events = filter_alarm_events(active_events, selected)
        rows = [
            (event.occurred_at.strftime("%H:%M:%S"), event.severity, event.source, event.message)
            for event in events
        ]
        # U01-U11: kullanıcı isteği (2026-09-22) - "Uyarı" filtresi
        # işaretliyken, şu an aktif olan Start engellerini de aynı tabloda
        # göster. Bunlar `AlarmRepository`'de KAYITLI DEĞİL - "ŞİMDİ" ile
        # işaretlenir (gerçek bir olay zaman damgası değil, canlı durumdur),
        # Reset'ten etkilenmez, koşul geçince satır anında kaybolur.
        if SEVERITY_WARNING in selected:
            for message in self._live_warning_messages:
                rows.append(("ŞİMDİ", SEVERITY_WARNING, "PLC", message))
        # M01-M09 (HMI-A05, C06_1 audit, 2026-09-22): aynı desen - canlı,
        # `AlarmRepository`'de KAYITLI DEĞİL, "Mesaj" filtresi işaretliyken
        # görünür.
        if SEVERITY_MESSAGE in selected:
            for message in self._live_message_texts:
                rows.append(("ŞİMDİ", SEVERITY_MESSAGE, "PLC", message))
        table = self._alarm_table
        table.setRowCount(len(rows))
        for row, (occurred_text, severity, source, message) in enumerate(rows):
            values = [occurred_text, SEVERITY_LABELS_TR.get(severity, severity), source, message]
            color = SEVERITY_ROW_COLOR.get(severity, COLORS["text_primary"])
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 1:
                    item.setForeground(QColor(color))
                table.setItem(row, col, item)

    # -- data binding ---------------------------------------------------------

    def _on_snapshot(self, snap: MachineSnapshot) -> None:
        stale = snap.stale

        self._x_readout.set_value("--" if stale else f"{snap.x_actual_pos:.1f}")
        self._y_readout.set_value("--" if stale else f"{snap.y_actual_pos:+.2f}")
        self._cycle_readout.set_value(cycle_state_label(snap.cycle_state) if not stale else "--")

        self._progress.setValue(0 if stale else int(round(snap.cycle_progress)))

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

        # U01-U11'i alarm tablosuna da aktar (kullanıcı isteği, 2026-09-22) -
        # her snapshot'ta yeniden hesaplanır, `AlarmRepository`'ye yazılmaz.
        self._live_warning_messages = reasons

        # PLC-HMI-20260922-18 (HMI-A05): M01-M07/M09 - cycle_state sürdüğü
        # sürece görünür. M08 - move_to_start_status() İLK KEZ "done" olan
        # tick'te bir kez (edge), sonrakilerde tekrar eklenmez.
        messages: list[str] = []
        state_message = compute_active_state_message(snap)
        if state_message is not None:
            messages.append(state_message)
        move_to_start_done_now = self._service.move_to_start_status() == "done"
        if move_to_start_done_now and not self._move_to_start_was_done:
            messages.append("[M08] Başlangıç konumuna dönüş tamamlandı.")
        self._move_to_start_was_done = move_to_start_done_now
        self._live_message_texts = messages

        self._refresh_alarm_table()
