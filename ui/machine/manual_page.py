"""Screen B — Manuel / Servis ekranı (integration brief section 8-B).

Jog / blade / clamp controls only take effect while MANUAL mode is active
and no auto cycle is running — enforced both here (visual disable) and
again inside MachineService (the real interlock always lives in the PLC,
brief section 6 & 26)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from core.cycle_state import AUTO_CYCLE_ACTIVE_STATES, CycleState
from core.models import MachineSnapshot
from core.parameters import PARAMETER_SPECS
from services.machine_service import MachineService
from ui.machine.theme import COLORS, base_font
from ui.machine.widgets import Card, HoldButton, ProcessStatusCard, Readout, touch_button

# PLC-HMI-20260921-11: "3 saniye basılı tutulunca iki eksen otomatik
# başlangıca dönsün" - kullanıcı talebi, sabit ve tek yerde tanımlı.
MOVE_TO_START_HOLD_MS = 3000


class ManualPage(QWidget):
    def __init__(self, service: MachineService, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = service
        # Kullanıcı isteği (2026-09-21): jog hızı artık ayrı bir "JOG Yavaş/
        # Hızlı" seçimi değil, doğrudan ilgili eksenin gerçek PLC parametresi
        # (`lr_x_jog_velocity`/`lr_y_jog_velocity`) - kazara değiştirmeyi
        # önlemek için bir "Düzenle" tik kutusu açılmadan alan düzenlenemez.
        self._jog_dirty: set[str] = set()
        self._jog_velocity_widgets: dict[str, tuple[QDoubleSpinBox, QCheckBox]] = {}
        # PLC-HMI-20260921-09: Aşağı için PLC-onaylı bir "kabul" biti yok -
        # yalnız son gönderilen komutu (kanıt değil) göstermek için yerel iz.
        self._blade_last_cmd: str | None = None
        self._clamp_last_cmd: str | None = None
        # PLC-HMI-20260921-11: 3 saniye kesintisiz basılı tutuş - erken
        # bırakma/izin kaybı/stale/odak kaybı/sayfa değişimi anında iptal
        # eder, yalnız süre TAM dolunca tek pulse gönderir.
        self._move_to_start_holding = False
        self._move_to_start_hold_timer = QTimer(self)
        self._move_to_start_hold_timer.setSingleShot(True)
        self._move_to_start_hold_timer.timeout.connect(self._on_move_to_start_hold_complete)
        self._move_to_start_progress_timer = QTimer(self)
        self._move_to_start_progress_timer.setInterval(100)
        self._move_to_start_progress_timer.timeout.connect(self._update_move_to_start_progress)
        self._build_ui()
        self._update_move_to_start_hint()
        service.snapshotUpdated.connect(self._on_snapshot)
        service.commandWriteError.connect(self._on_command_write_error)

        app = QApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._on_application_state_changed)

    # -- safety: never leave a jog request stuck TRUE --------------------

    def _on_application_state_changed(self, state: Qt.ApplicationState) -> None:
        if state != Qt.ApplicationState.ApplicationActive:
            self._service.release_all_jog()
            self._cancel_move_to_start_hold()

    def hideEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._service.release_all_jog()
        self._cancel_move_to_start_hold()
        super().hideEvent(event)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("MANUEL / SERVİS")
        title.setFont(base_font(14, bold=True))
        # Kullanıcı isteği (2026-09-23): ikinci bir "OTO MODU ETKİNLEŞTİR"
        # butonu eklemek yerine, TEK butonun metni basılınca ne olacağını
        # gösterir - Manuel'deyken "OTO MODU ETKİNLEŞTİR" (basınca Auto'ya
        # geçer), Auto'dayken "MANUEL MODU ETKİNLEŞTİR" (basınca Manuel'e
        # geçer). Ana ekrandaki "oto moda geçin" uyarısına karşılık gelen
        # buton artık açıkça görünür - ayrı bir buton yok diye kafa
        # karışıklığı olmasın.
        self._manual_mode_btn = touch_button(
            "MANUEL MODU ETKİNLEŞTİR", object_name="navButton", checkable=True
        )
        self._manual_mode_btn.clicked.connect(self._service.set_manual_mode)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self._manual_mode_btn)
        root.addLayout(header)

        axes_row = QHBoxLayout()
        axes_row.setSpacing(10)
        axes_row.addWidget(self._build_x_axis_card())
        axes_row.addWidget(self._build_y_axis_card())
        root.addLayout(axes_row)

        # Kullanıcı isteği (2026-09-22, ekran görüntüsü): "Başlangıç Konumuna
        # Dön" butonu (HoldButton, sabit PRIMARY_ACTION_HEIGHT=64) ve karşısındaki
        # "BAŞLANGIÇ KONUMU" durum kutusu (ProcessStatusCard, kendi içeriğine
        # göre doğal yükseklik) farklı yükseklikteydi - bu satırdan sonraki her
        # şey (Actual Position, Servo) X/Y kartları arasında birkaç piksel kaymış,
        # sayfa "yamuk" görünüyordu. İkisi aynı yüksekliğe sabitlenir.
        row_height = self._move_to_start_status.sizeHint().height()
        self._move_to_start_btn.setFixedHeight(row_height)
        self._move_to_start_status.setFixedHeight(row_height)

        lower_row = QHBoxLayout()
        lower_row.setSpacing(10)
        lower_row.addWidget(self._build_feed_card())
        lower_row.addWidget(self._build_blade_card())
        lower_row.addWidget(self._build_clamp_card())
        root.addLayout(lower_row)

        root.addStretch(1)

    def _build_x_axis_card(self) -> Card:
        card = Card("X Ekseni")
        row = QHBoxLayout()
        self._x_minus = HoldButton("X -")
        self._x_plus = HoldButton("X +")
        self._x_minus.held.connect(lambda active: self._service.jog_x(-1, active))
        self._x_plus.held.connect(lambda active: self._service.jog_x(1, active))
        row.addWidget(self._x_minus)
        row.addWidget(self._x_plus)
        card.body_layout().addLayout(row)
        card.body_layout().addLayout(self._build_jog_velocity_row("lr_x_jog_velocity"))

        # PLC-HMI-20260921-11 + kullanıcı isteği (2026-09-21): "Başlangıç
        # Konumuna Dön" butonu buraya (sol/X kartı) taşındı; durum bilgisi
        # sağda (Y kartı) kalıyor.
        card.body_layout().addWidget(self._build_move_to_start_button())

        self._x_pos_readout = Readout("Actual Position", "0.0", "mm")
        card.body_layout().addWidget(self._x_pos_readout)
        self._x_servo_status = ProcessStatusCard("Servo")
        card.body_layout().addWidget(self._x_servo_status)
        card.body_layout().addStretch(1)
        return card

    def _build_y_axis_card(self) -> Card:
        card = Card("Y Ekseni")
        row = QHBoxLayout()
        self._y_minus = HoldButton("Y -")
        self._y_plus = HoldButton("Y +")
        self._y_minus.held.connect(lambda active: self._service.jog_y(-1, active))
        self._y_plus.held.connect(lambda active: self._service.jog_y(1, active))
        row.addWidget(self._y_minus)
        row.addWidget(self._y_plus)
        card.body_layout().addLayout(row)
        card.body_layout().addLayout(self._build_jog_velocity_row("lr_y_jog_velocity"))

        self._move_to_start_status = ProcessStatusCard("Başlangıç Konumu")
        card.body_layout().addWidget(self._move_to_start_status)

        self._y_pos_readout = Readout("Actual Position", "+0.00", "mm")
        card.body_layout().addWidget(self._y_pos_readout)
        self._y_servo_status = ProcessStatusCard("Servo")
        card.body_layout().addWidget(self._y_servo_status)
        card.body_layout().addStretch(1)
        return card

    def _build_move_to_start_button(self) -> HoldButton:
        # PLC-HMI-20260921-11: eski "MERKEZE GİT / Y=0" (yalnız Y) tek bir
        # "Başlangıç Konumuna Dön" (X+Y) butonuyla değiştirildi - kullanıcı
        # talebi, kazara dokunmayı önlemek için 3 saniye basılı tutuş şartlı.
        # "3 sn basılı tutun" bilgisi butonun kendi içinde, sağ-alt köşede.
        self._move_to_start_btn = HoldButton("")
        btn_layout = QVBoxLayout(self._move_to_start_btn)
        btn_layout.setContentsMargins(12, 6, 12, 4)
        btn_layout.setSpacing(2)
        self._move_to_start_label = QLabel("Başlangıç Konumuna Dön")
        self._move_to_start_label.setFont(base_font(12, bold=True))
        self._move_to_start_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(self._move_to_start_label)
        btn_layout.addStretch(1)
        self._move_to_start_hint = QLabel()
        self._move_to_start_hint.setFont(base_font(8))
        self._move_to_start_hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self._move_to_start_hint.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        btn_layout.addWidget(self._move_to_start_hint)
        self._move_to_start_btn.held.connect(self._on_move_to_start_held)
        return self._move_to_start_btn

    def _build_jog_velocity_row(self, key: str) -> QHBoxLayout:
        """Kullanıcı isteği (2026-09-21): "JOG Yavaş/Hızlı" yerine, ilgili
        eksenin gerçek PLC jog hızı parametresine (zaten Ayarlar'da var olan
        `lr_x_jog_velocity`/`lr_y_jog_velocity`) doğrudan bağlı bir giriş -
        yanındaki "Düzenle" tik kutusu işaretlenmeden alan düzenlenemez,
        yanlışlıkla değiştirmeyi önlemek için."""
        spec = next(s for s in PARAMETER_SPECS if s.key == key)
        row = QHBoxLayout()
        label = QLabel(f"{spec.label_tr}:")
        spin = QDoubleSpinBox()
        spin.setRange(spec.min_value, spec.max_value)
        spin.setDecimals(1)
        spin.setSuffix(f" {spec.unit}")
        spin.setEnabled(False)
        spin.blockSignals(True)
        spin.setValue(self._service.get_parameter_value(key))
        spin.blockSignals(False)
        # Yalnız gerçek kullanıcı düzenlemesinde tetiklenir - programatik
        # setValue çağrıları blockSignals ile korunuyor (settings_page.py'deki
        # aynı "dirty" deseni, 2026-09-16 bug fix).
        spin.valueChanged.connect(lambda _v, k=key: self._jog_dirty.add(k))
        spin.editingFinished.connect(lambda k=key: self._commit_jog_velocity(k))
        checkbox = QCheckBox("Düzenle")
        checkbox.toggled.connect(lambda checked, k=key: self._on_jog_edit_toggled(k, checked))
        row.addWidget(label)
        row.addWidget(spin, 1)
        row.addWidget(checkbox)
        self._jog_velocity_widgets[key] = (spin, checkbox)
        return row

    def _on_jog_edit_toggled(self, key: str, checked: bool) -> None:
        spin, _checkbox = self._jog_velocity_widgets[key]
        spin.setEnabled(checked)
        if not checked:
            # Kilitlenince yarım kalmış bir düzenleme varsa atılır - canlı
            # PLC değerine geri dönülür, yanlışlıkla kaydedilmez.
            self._jog_dirty.discard(key)
            spin.blockSignals(True)
            spin.setValue(self._service.get_parameter_value(key))
            spin.blockSignals(False)

    def _commit_jog_velocity(self, key: str) -> None:
        if key not in self._jog_dirty:
            return  # editingFinished odak kaybında da tetiklenir, değişiklik olmayabilir
        spin, _checkbox = self._jog_velocity_widgets[key]
        try:
            self._service.set_parameter(key, spin.value())
        except ValueError as exc:
            QMessageBox.warning(self, "Geçersiz Değer", str(exc))
            spin.blockSignals(True)
            spin.setValue(self._service.get_parameter_value(key))
            spin.blockSignals(False)
        self._jog_dirty.discard(key)

    def _build_feed_card(self) -> Card:
        card = Card("Perde Besleme (Diagnostic)")
        self._feed_forward_status = ProcessStatusCard("Perde İleri Input")
        self._feed_reverse_status = ProcessStatusCard("Perde Geri Input")
        self._feed_running_status = ProcessStatusCard("Besleme Motoru")
        card.body_layout().addWidget(self._feed_forward_status)
        card.body_layout().addWidget(self._feed_reverse_status)
        card.body_layout().addWidget(self._feed_running_status)
        return card

    def _build_blade_card(self) -> Card:
        # PLC-HMI-20260921-09: dört BOOL pulse buton - Yukarı (mevcut,
        # xBladeRetractRequest) + Aşağı (yeni, xBladeDownRequest). Aşağı için
        # PLC-onaylı bir "kabul" biti yok - Sensör (BladeZDown) gerçek
        # kanıttır, "Son Komut" yalnız gönderimi gösterir.
        card = Card("Bıçak")
        self._blade_retract_btn = touch_button("Bıçağı Geri Çek (Yukarı)")
        self._blade_retract_btn.clicked.connect(self._on_blade_retract_clicked)
        card.body_layout().addWidget(self._blade_retract_btn)
        self._blade_down_btn = touch_button("Bıçak Aşağı")
        self._blade_down_btn.clicked.connect(self._on_blade_down_clicked)
        card.body_layout().addWidget(self._blade_down_btn)
        self._blade_status = ProcessStatusCard("Sensör")
        card.body_layout().addWidget(self._blade_status)
        self._blade_accept_status = ProcessStatusCard("Son Komut")
        card.body_layout().addWidget(self._blade_accept_status)
        return card

    def _build_clamp_card(self) -> Card:
        card = Card("Perde Baskısı")
        self._clamp_retract_btn = touch_button("Baskıyı Geri Çek (Yukarı)")
        self._clamp_retract_btn.clicked.connect(self._on_clamp_retract_clicked)
        card.body_layout().addWidget(self._clamp_retract_btn)
        self._clamp_down_btn = touch_button("Baskı Aşağı")
        self._clamp_down_btn.clicked.connect(self._on_clamp_down_clicked)
        card.body_layout().addWidget(self._clamp_down_btn)
        self._clamp_status = ProcessStatusCard("Sensör")
        card.body_layout().addWidget(self._clamp_status)
        self._clamp_accept_status = ProcessStatusCard("Son Komut")
        card.body_layout().addWidget(self._clamp_accept_status)
        return card

    # -- blade/clamp click handlers (track last-sent direction, not proof) --

    def _on_blade_retract_clicked(self) -> None:
        # C0.4 takip notu: yalnız gönderim GERÇEKTEN kalktıysa (izin +
        # tag'ler tamam) "gönderildi" göster - iyimser değil.
        if self._service.request_blade_retract():
            self._blade_last_cmd = "up"

    def _on_blade_down_clicked(self) -> None:
        if self._service.request_blade_down():
            self._blade_last_cmd = "down"

    def _on_clamp_retract_clicked(self) -> None:
        if self._service.request_clamp_retract():
            self._clamp_last_cmd = "up"

    def _on_clamp_down_clicked(self) -> None:
        if self._service.request_clamp_down():
            self._clamp_last_cmd = "down"

    def _on_command_write_error(self, tag: str, reason: str) -> None:
        """C0.4 takip notu: "gerçek OPC yazma sonucunu göster, yalnız demo
        testi yeterli değil" - `MachineService.commandWriteError`, PLC bu
        pulse'u gerçekten reddettiğinde (`errorOccurred`) buraya taşır."""
        if tag in ("cmd_blade_retract", "cmd_blade_down"):
            self._blade_last_cmd = "error"
            mechanism = "Bıçak"
        elif tag in ("cmd_clamp_retract", "cmd_clamp_down"):
            self._clamp_last_cmd = "error"
            mechanism = "Baskı"
        elif tag == "cmd_move_to_start":
            mechanism = "Başlangıç konumuna dönüş"
        else:
            return
        QMessageBox.warning(
            self,
            "Yazma Reddedildi",
            f"{mechanism} komutu PLC tarafından reddedildi.\n\nGerçek OPC UA hatası:\n{reason}",
        )

    # -- "Başlangıç Konumuna Dön": 3 saniye kesintisiz basılı tutuş ---------

    def _on_move_to_start_held(self, active: bool) -> None:
        if active:
            self._start_move_to_start_hold()
        else:
            self._cancel_move_to_start_hold()

    def _start_move_to_start_hold(self) -> None:
        if self._move_to_start_holding:
            return
        if not self._service.move_to_start_allowed_now():
            return
        self._move_to_start_holding = True
        self._move_to_start_hold_timer.start(MOVE_TO_START_HOLD_MS)
        self._move_to_start_progress_timer.start()
        self._update_move_to_start_progress()

    def _cancel_move_to_start_hold(self) -> None:
        # Erken bırakma, pointer butondan çıkması, odak/sayfa kaybı, izin
        # kaybı, stale veya bağlantı kopması - hepsi buraya düşer. Sayaç
        # tam sıfırlanır; bir sonraki deneme YENİ, baştan bir basış ister.
        if not self._move_to_start_holding:
            return
        self._move_to_start_holding = False
        self._move_to_start_hold_timer.stop()
        self._move_to_start_progress_timer.stop()
        self._update_move_to_start_hint()

    def _update_move_to_start_progress(self) -> None:
        remaining_ms = self._move_to_start_hold_timer.remainingTime()
        if remaining_ms < 0:
            return
        self._move_to_start_hint.setText(f"Basılı tutun… {remaining_ms / 1000:.1f}s")

    def _on_move_to_start_hold_complete(self) -> None:
        # Süre TAM dolduğunda - parmak hâlâ basılı olsa bile - tek pulse.
        # HoldButton `held(False)` gelene kadar (gerçek bırakışta)
        # `_move_to_start_holding` True kalır, bu yüzden aynı basış ikinci
        # bir sayaç/pulse üretemez (görev notu: "auto-repeat kapalı").
        self._move_to_start_progress_timer.stop()
        self._update_move_to_start_hint()
        self._service.request_move_to_start()

    def _update_move_to_start_hint(self) -> None:
        if self._service.is_parameter_confirmed(
            "lr_x_cut_start_pos"
        ) and self._service.is_parameter_confirmed("lr_y_center_position"):
            x = self._service.get_parameter_value("lr_x_cut_start_pos")
            y = self._service.get_parameter_value("lr_y_center_position")
            self._move_to_start_hint.setText(f"3 saniye basılı tutun — X={x:g} Y={y:g} mm")
        else:
            self._move_to_start_hint.setText("3 saniye basılı tutun — X + Y")

    # PLC-HMI-20260921-14: genel "HATA - PLC REDDETTİ" yerine duruma özgü
    # doğru ifadeler. Error öncelikli; Aborted tek başına "talep reddi" ile
    # "iptal"i ayrıştıramaz (kaynakta tek bit) - ikisi birlikte söylenir.
    _MOVE_TO_START_STATUS_LABELS = {
        "idle": ("—", "inactive"),
        "sent": ("GÖNDERİLDİ", "warn"),
        "busy": ("HAREKET EDİYOR", "warn"),
        "stopping": ("DÖNÜŞ DURDURULUYOR", "warn"),
        "done": ("TAMAMLANDI", "ok"),
        "aborted": ("TALEP REDDEDİLDİ VEYA DÖNÜŞ İPTAL EDİLDİ", "fault"),
        "error": ("BAŞLANGICA DÖNÜŞ ARIZASI", "fault"),
    }

    @staticmethod
    def _pneumatic_feedback(retract_accepted: bool, last_cmd: str | None) -> tuple[str, str]:
        """PLC-HMI-20260921-09: Aşağı için PLC-onaylı bir kabul biti yok -
        Yukarı kabulünü PLC'den (kanıt), Aşağı'yı yalnız "gönderildi" olarak
        (kanıt DEĞİL) gösterir; ikisi karıştırılmaz. "error" gerçek bir OPC UA
        reddini (`commandWriteError`) yansıtır."""
        if retract_accepted:
            return "YUKARI: KABUL EDİLDİ", "ok"
        if last_cmd == "error":
            return "HATA — PLC REDDETTİ", "fault"
        if last_cmd == "down":
            return "AŞAĞI: GÖNDERİLDİ", "warn"
        if last_cmd == "up":
            return "YUKARI: BEKLENİYOR", "inactive"
        return "—", "inactive"

    # -- data binding ---------------------------------------------------------

    def _on_snapshot(self, snap: MachineSnapshot) -> None:
        try:
            state = CycleState(snap.cycle_state)
        except ValueError:
            state = None
        manual_allowed = snap.manual_mode and state not in AUTO_CYCLE_ACTIVE_STATES and not snap.stale

        self._manual_mode_btn.blockSignals(True)
        self._manual_mode_btn.setChecked(snap.manual_mode)
        self._manual_mode_btn.blockSignals(False)
        # Buton, basılınca GEÇİLECEK moda göre etiketlenir (görev notu,
        # 2026-09-23) - Manuel'deyken "OTO MODU ETKİNLEŞTİR" gösterir.
        self._manual_mode_btn.setText(
            "OTO MODU ETKİNLEŞTİR" if snap.manual_mode else "MANUEL MODU ETKİNLEŞTİR"
        )
        # H2 (2026-09-18, kullanıcı test notu): "otomatik mod aktifken ve
        # kesim devam ederken buton aktif kalıyordu" - cycle_active TRUE
        # olduğu SÜRECE (yalnız CUTTING değil; hazırlık/dönüş dahil tüm
        # çevrim) buton devre dışı. Stale/bağlantısızken de fail-closed -
        # PLC'nin gerçek modunu bilmeden değişikliğe izin verilmez. Gerçek
        # engel `MachineService.set_manual_mode` içinde de var; bu sadece
        # görsel/erken engel.
        self._manual_mode_btn.setEnabled(not snap.cycle_active and not snap.stale)

        for btn in (
            self._x_minus,
            self._x_plus,
            self._y_minus,
            self._y_plus,
        ):
            btn.setEnabled(manual_allowed)

        # Kilitliyken (Düzenle işaretsiz) her zaman canlı PLC değerini
        # göster; işaretliyken kullanıcının bitirmediği bir düzenlemenin
        # üzerine yazma (settings_page.py'deki "dirty" deseniyle aynı).
        for key, (spin, _checkbox) in self._jog_velocity_widgets.items():
            if key not in self._jog_dirty:
                spin.blockSignals(True)
                spin.setValue(self._service.get_parameter_value(key))
                spin.blockSignals(False)

        # PLC-HMI-20260921-11: "İzin HMI'da yeniden üretilmez" - yalnız
        # servisin `move_to_start_allowed_now()`'u (Allowed okunur, ayrıntılı
        # ön koşul tekrarlanmaz) buton etkinliğini belirler. Basılı tutuş
        # SÜRERKEN izin kaybolursa hemen iptal edilir - "izin şartları 3
        # saniye boyunca korunmalı" (görev notu).
        move_to_start_ok = self._service.move_to_start_allowed_now()
        self._move_to_start_btn.setEnabled(move_to_start_ok)
        if self._move_to_start_holding and not move_to_start_ok:
            self._cancel_move_to_start_hold()
        move_to_start_tag_reason = "PLC'de xMoveToStartRequest/Allowed/Busy/Done/Aborted/Error henüz online doğrulanmadı."
        move_to_start_tags_configured = self._service.move_to_start_tags_configured()
        self._move_to_start_btn.setToolTip("" if move_to_start_tags_configured else move_to_start_tag_reason)
        if move_to_start_tags_configured:
            status_text, status_mood = self._MOVE_TO_START_STATUS_LABELS[self._service.move_to_start_status()]
        else:
            # PLC-HMI-20260921-12 takip notu: eksik tag boş tireyle
            # bırakılmasın - kısa, açık bir neden gösterilsin.
            status_text, status_mood = "TAG EKSİK", "fault"
        self._move_to_start_status.set_status(status_text, status_mood)

        # PLC-HMI-20260921-09: bıçak/baskı butonları artık kendi (daha
        # eksiksiz) "ortak izin" kontrolüyle gater - tek kaynak MachineService,
        # burada tekrar hesaplanmaz. Aşağı, Yukarı'dan ek şartlarla (hazırlık
        # kilidi, besleme kapalı) daha kısıtlı.
        pneumatic_allowed = self._service.manual_pneumatic_allowed()
        self._blade_retract_btn.setEnabled(pneumatic_allowed)
        self._clamp_retract_btn.setEnabled(pneumatic_allowed)
        self._blade_down_btn.setEnabled(self._service.manual_blade_down_allowed())
        self._clamp_down_btn.setEnabled(self._service.manual_clamp_down_allowed())
        # Devre dışıysa nedeni ayırt et: PLC'de tag hâlâ tanımsız mı (online
        # doğrulama bekliyor), yoksa yalnızca şu an izin şartları mı sağlanmıyor.
        self._blade_down_btn.setToolTip(
            "" if self._service.blade_down_tags_configured()
            else "PLC'de xBladeDownRequest/xAlarmStopRequest/xManualPreparationRequired henüz online doğrulanmadı."
        )
        self._clamp_down_btn.setToolTip(
            "" if self._service.clamp_down_tags_configured()
            else "PLC'de xClampDownRequest/xAlarmStopRequest/xManualPreparationRequired henüz online doğrulanmadı."
        )

        if not snap.manual_mode:
            self._blade_last_cmd = None
            self._clamp_last_cmd = None

        self._x_pos_readout.set_value("--" if snap.stale else f"{snap.x_actual_pos:.1f}")
        self._y_pos_readout.set_value("--" if snap.stale else f"{snap.y_actual_pos:+.2f}")

        self._x_servo_status.set_status(
            "FAULT" if snap.x_fault else ("READY" if snap.x_servo_ready else "--"),
            "fault" if snap.x_fault else ("ok" if snap.x_servo_ready else "inactive"),
        )
        self._y_servo_status.set_status(
            "FAULT" if snap.y_fault else ("READY" if snap.y_servo_ready else "--"),
            "fault" if snap.y_fault else ("ok" if snap.y_servo_ready else "inactive"),
        )

        self._feed_forward_status.set_status(
            "AKTİF" if snap.feed_forward_input else "--", "ok" if snap.feed_forward_input else "inactive"
        )
        self._feed_reverse_status.set_status(
            "AKTİF" if snap.feed_reverse_input else "--", "ok" if snap.feed_reverse_input else "inactive"
        )
        self._feed_running_status.set_status(
            "ÇALIŞIYOR" if snap.feed_running else "DURDU", "ok" if snap.feed_running else "inactive"
        )

        # Kullanıcı isteği (2026-09-18): "AÇIK" yerine "YUKARI" gösterilsin.
        # Not: PLC-HMI-20260918-06 sözleşmesi FALSE'un ayrı/doğrulanmış bir
        # yukarı sensörü OLMADIĞINI, kullanıcının kabul ettiği mekanik
        # açıklık olduğunu belirtiyor - okunan tag ve mantık değişmedi,
        # yalnızca ekran metni kullanıcının tercihine göre güncellendi.
        self._blade_status.set_status(
            "AŞAĞI" if snap.blade_down else "YUKARI", "warn" if snap.blade_down else "ok"
        )
        self._clamp_status.set_status(
            "AŞAĞI" if snap.clamp_down else "YUKARI", "warn" if snap.clamp_down else "ok"
        )
        self._blade_accept_status.set_status(
            *self._pneumatic_feedback(snap.blade_retract_accepted, self._blade_last_cmd)
        )
        self._clamp_accept_status.set_status(
            *self._pneumatic_feedback(snap.clamp_retract_accepted, self._clamp_last_cmd)
        )
