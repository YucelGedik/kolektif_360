"""Screen B — Manuel / Servis ekranı (integration brief section 8-B).

Jog / blade / clamp controls only take effect while MANUAL mode is active
and no auto cycle is running — enforced both here (visual disable) and
again inside MachineService (the real interlock always lives in the PLC,
brief section 6 & 26)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from core.cycle_state import AUTO_CYCLE_ACTIVE_STATES, CycleState
from core.models import MachineSnapshot
from services.machine_service import MachineService
from ui.machine.theme import MIN_TOUCH_HEIGHT, base_font
from ui.machine.widgets import Card, HoldButton, ProcessStatusCard, Readout, touch_button


class ManualPage(QWidget):
    navigateRequested = Signal(str)  # "machine_main"

    def __init__(self, service: MachineService, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = service
        self._x_jog_fast = False
        self._y_jog_fast = False
        self._build_ui()
        service.snapshotUpdated.connect(self._on_snapshot)

        app = QApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._on_application_state_changed)

    # -- safety: never leave a jog request stuck TRUE --------------------

    def _on_application_state_changed(self, state: Qt.ApplicationState) -> None:
        if state != Qt.ApplicationState.ApplicationActive:
            self._service.release_all_jog()

    def hideEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._service.release_all_jog()
        super().hideEvent(event)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("MANUEL / SERVİS")
        title.setFont(base_font(14, bold=True))
        self._manual_mode_btn = touch_button(
            "MANUEL MODU ETKİNLEŞTİR", object_name="navButton", checkable=True
        )
        self._manual_mode_btn.clicked.connect(self._service.set_manual_mode)
        back_btn = touch_button("◀ ANA EKRAN", object_name="navButton")
        back_btn.clicked.connect(lambda: self.navigateRequested.emit("machine_main"))
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self._manual_mode_btn)
        header.addWidget(back_btn)
        root.addLayout(header)

        axes_row = QHBoxLayout()
        axes_row.setSpacing(10)
        axes_row.addWidget(self._build_x_axis_card())
        axes_row.addWidget(self._build_y_axis_card())
        root.addLayout(axes_row)

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
        self._x_minus.held.connect(lambda active: self._service.jog_x(-1, active, self._x_jog_fast))
        self._x_plus.held.connect(lambda active: self._service.jog_x(1, active, self._x_jog_fast))
        row.addWidget(self._x_minus)
        row.addWidget(self._x_plus)
        card.body_layout().addLayout(row)
        card.body_layout().addLayout(self._build_jog_speed_row(lambda fast: setattr(self, "_x_jog_fast", fast)))

        # X ekseninde Y'deki "MERKEZE GİT" gibi bir referans komutu yok (brif
        # bölüm 8); alttaki Actual Position/Servo satırlarının Y kartıyla
        # aynı hizada kalması için o butonun yüksekliğinde boş alan bırakılır.
        spacer = QWidget()
        spacer.setFixedHeight(MIN_TOUCH_HEIGHT)
        card.body_layout().addWidget(spacer)

        self._x_pos_readout = Readout("Actual Position", "0.0", "mm")
        card.body_layout().addWidget(self._x_pos_readout)
        self._x_servo_status = ProcessStatusCard("Servo")
        card.body_layout().addWidget(self._x_servo_status)
        return card

    def _build_y_axis_card(self) -> Card:
        card = Card("Y Ekseni")
        row = QHBoxLayout()
        self._y_minus = HoldButton("Y -")
        self._y_plus = HoldButton("Y +")
        self._y_minus.held.connect(lambda active: self._service.jog_y(-1, active, self._y_jog_fast))
        self._y_plus.held.connect(lambda active: self._service.jog_y(1, active, self._y_jog_fast))
        row.addWidget(self._y_minus)
        row.addWidget(self._y_plus)
        card.body_layout().addLayout(row)
        card.body_layout().addLayout(self._build_jog_speed_row(lambda fast: setattr(self, "_y_jog_fast", fast)))

        self._y_center_btn = touch_button("MERKEZE GİT / Y=0")
        self._y_center_btn.clicked.connect(self._service.y_center)
        card.body_layout().addWidget(self._y_center_btn)

        self._y_pos_readout = Readout("Actual Position", "+0.00", "mm")
        card.body_layout().addWidget(self._y_pos_readout)
        self._y_servo_status = ProcessStatusCard("Servo")
        card.body_layout().addWidget(self._y_servo_status)
        return card

    def _build_jog_speed_row(self, set_fast) -> QHBoxLayout:
        row = QHBoxLayout()
        slow_btn = touch_button("JOG Yavaş", checkable=True)
        fast_btn = touch_button("JOG Hızlı", checkable=True)
        slow_btn.setChecked(True)

        def pick(fast: bool) -> None:
            set_fast(fast)
            slow_btn.setChecked(not fast)
            fast_btn.setChecked(fast)

        slow_btn.clicked.connect(lambda: pick(False))
        fast_btn.clicked.connect(lambda: pick(True))
        row.addWidget(slow_btn)
        row.addWidget(fast_btn)
        return row

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
        # PLC-HMI-20260918-06: yalnız "Yukarı/Geri Çek" gerçek, PLC-kabullü
        # bir request'e sahip (GVL.xBladeRetractRequest, pulse). Manuel
        # "Aşağı" için PLC'de henüz bir request tanımlı değil - ayrı, açık
        # bir PLC görevi; tag adı uydurulup buton işlevli gösterilmez.
        card = Card("Bıçak")
        self._blade_retract_btn = touch_button("Bıçağı Geri Çek (Yukarı)")
        self._blade_retract_btn.clicked.connect(self._service.request_blade_retract)
        card.body_layout().addWidget(self._blade_retract_btn)
        self._blade_down_btn = touch_button("Bıçak Aşağı")
        self._blade_down_btn.setEnabled(False)
        self._blade_down_btn.setToolTip(
            "PLC tarafında manuel Aşağı talebi henüz tanımlı değil (ayrı görev, açık)."
        )
        card.body_layout().addWidget(self._blade_down_btn)
        self._blade_status = ProcessStatusCard("Sensör")
        card.body_layout().addWidget(self._blade_status)
        self._blade_accept_status = ProcessStatusCard("Yukarı Talebi")
        card.body_layout().addWidget(self._blade_accept_status)
        return card

    def _build_clamp_card(self) -> Card:
        card = Card("Perde Baskısı")
        self._clamp_retract_btn = touch_button("Baskıyı Geri Çek (Yukarı)")
        self._clamp_retract_btn.clicked.connect(self._service.request_clamp_retract)
        card.body_layout().addWidget(self._clamp_retract_btn)
        self._clamp_down_btn = touch_button("Baskı Aşağı")
        self._clamp_down_btn.setEnabled(False)
        self._clamp_down_btn.setToolTip(
            "PLC tarafında manuel Aşağı talebi henüz tanımlı değil (ayrı görev, açık)."
        )
        card.body_layout().addWidget(self._clamp_down_btn)
        self._clamp_status = ProcessStatusCard("Sensör")
        card.body_layout().addWidget(self._clamp_status)
        self._clamp_accept_status = ProcessStatusCard("Yukarı Talebi")
        card.body_layout().addWidget(self._clamp_accept_status)
        return card

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
            self._y_center_btn,
            self._blade_retract_btn,
            self._clamp_retract_btn,
        ):
            btn.setEnabled(manual_allowed)
        # Aşağı butonları kalıcı olarak devre dışı - PLC'de henüz bir
        # request tanımlı değil (görev notu, tag adı uydurulmaz).

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
            "KABUL EDİLDİ" if snap.blade_retract_accepted else "BEKLENİYOR",
            "ok" if snap.blade_retract_accepted else "inactive",
        )
        self._clamp_accept_status.set_status(
            "KABUL EDİLDİ" if snap.clamp_retract_accepted else "BEKLENİYOR",
            "ok" if snap.clamp_retract_accepted else "inactive",
        )
