"""Geçici mühendislik diagnostic ekranı ve Vision veri simülatörü penceresi
(görev: .ai/HMI_TEMP_VISION_SIMULATOR_TASK.md, PLC-HMI-20260917-02).

GEÇİCİDİR. Yalnız Mühendislik Erişimi açıkken Ayarlar sayfasından ulaşılır
(ayrı gizli menü/parola değil - mevcut yetki kapısı yeniden kullanılıyor,
Faz 1 notu). Kullanıcının isteği üzerine (2026-09-17) modeless bir pencere
(`show()`, `exec()` değil): ana makine kontrol ekranı bu pencere açıkken de
kullanılabilir olsun ki mühendis Vision paketi beslerken aynı anda gerçek
Start/Stop/Jog ile çevrimi paralel çalıştırabilsin.

Açılışta hiçbir şey yazılmaz: VisionReady/LineValid/CutPermit/ZDownRequest
varsayılan FALSE gösterilir, ARM etmek bile tek başına bir yazı üretmez -
her yazı açık bir buton tıklamasının sonucudur.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)

from core.cycle_state import cycle_state_label
from core.models import ConnectionState, MachineSnapshot
from services.machine_service import MachineService
from services.vision_simulator import (
    AUTO_CAMERA_DEFAULT_PERIOD_MS,
    AUTO_CAMERA_MAX_PERIOD_MS,
    AUTO_CAMERA_MIN_PERIOD_MS,
    VisionSimulatorService,
    sensor_hint,
)
from ui.machine.theme import COLORS, base_font
from ui.machine.widgets import touch_button, restyle


class VisionSimulatorDialog(QDialog):
    def __init__(
        self,
        vision_sim: VisionSimulatorService,
        machine_service: MachineService,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setModal(False)
        self.setWindowTitle("GEÇİCİ VISION SİMÜLATÖRÜ (Mühendislik)")
        self.resize(520, 640)

        self._sim = vision_sim
        self._service = machine_service

        self._build_ui()

        self._sim.armedChanged.connect(self._on_armed_changed)
        self._sim.autoCameraChanged.connect(self._on_auto_camera_changed)
        self._sim.packetResult.connect(self._on_packet_result)
        self._sim.lastErrorChanged.connect(self._on_error)
        self._service.snapshotUpdated.connect(self._on_snapshot)

        self._refresh_armed_ui()

    # -- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        banner = QLabel(
            "⚠ GEÇİCİ MÜHENDİSLİK EKRANI — Gerçek kamera yerine sınırlı Vision "
            "alanlarını PLC'ye yazar. Normal operatör kullanımı için değildir."
        )
        banner.setWordWrap(True)
        banner.setStyleSheet(f"color: {COLORS['warning']}; font-weight: 600;")
        root.addWidget(banner)

        status_frame = QFrame()
        status_frame.setObjectName("card")
        status_layout = QGridLayout(status_frame)
        self._source_label = QLabel("Kaynak: —")
        self._armed_label = QLabel("Durum: —")
        self._conn_label = QLabel("Bağlantı: —")
        self._error_label = QLabel("Son yazma hatası: —")
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(f"color: {COLORS['danger']};")
        status_layout.addWidget(self._source_label, 0, 0)
        status_layout.addWidget(self._armed_label, 0, 1)
        status_layout.addWidget(self._conn_label, 1, 0)
        status_layout.addWidget(self._error_label, 2, 0, 1, 2)
        root.addWidget(status_frame)

        arm_row = QHBoxLayout()
        self._arm_btn = touch_button("ARM (Vision Kaynağını Devral)")
        self._arm_btn.clicked.connect(self._on_arm_clicked)
        self._disarm_btn = touch_button("DISARM (Bırak)")
        self._disarm_btn.clicked.connect(self._on_disarm_clicked)
        arm_row.addWidget(self._arm_btn)
        arm_row.addWidget(self._disarm_btn)
        root.addLayout(arm_row)

        auto_box = QGroupBox("Otomatik Kamera / Düz Çizgi Masa Testi (önerilen)")
        auto_layout = QGridLayout(auto_box)
        auto_note = QLabel(
            "ARM edin, başlatın, sonra ana ekrandan Start verin. Heartbeat de "
            "dahil hedef/CutPermit/ZDownRequest PLC state'ine ve actual X'e göre "
            "kendiliğinden üretilir - paket/izin/heartbeat tıklamanız gerekmez. "
            "Sensörleri fiziksel olarak (mıknatısla) aşağıdaki ipucuna göre "
            "tetikleyin."
        )
        auto_note.setWordWrap(True)
        auto_note.setStyleSheet(f"color: {COLORS['text_secondary']};")
        auto_layout.addWidget(auto_note, 0, 0, 1, 2)
        auto_layout.addWidget(QLabel("Paket periyodu (ms)"), 1, 0)
        self._auto_period_spin = QSpinBox()
        self._auto_period_spin.setRange(AUTO_CAMERA_MIN_PERIOD_MS, AUTO_CAMERA_MAX_PERIOD_MS)
        self._auto_period_spin.setValue(AUTO_CAMERA_DEFAULT_PERIOD_MS)
        self._auto_period_spin.setSuffix(" ms")
        auto_layout.addWidget(self._auto_period_spin, 1, 1)

        # H6 (2026-09-18): ikinci, açıkça seçilen senaryo - varsayılan
        # "Düz Çizgi" değişmedi. Yalnız auto_camera pasifken değiştirilebilir.
        scenario_row = QHBoxLayout()
        self._scenario_straight_rb = QRadioButton("Düz Çizgi (varsayılan)")
        self._scenario_tilted_rb = QRadioButton("Eğimli Çizgi")
        self._scenario_straight_rb.setChecked(True)
        self._scenario_group = QButtonGroup(self)
        self._scenario_group.addButton(self._scenario_straight_rb)
        self._scenario_group.addButton(self._scenario_tilted_rb)
        scenario_row.addWidget(self._scenario_straight_rb)
        scenario_row.addWidget(self._scenario_tilted_rb)
        auto_layout.addLayout(scenario_row, 2, 0, 1, 2)

        auto_layout.addWidget(QLabel("Eğim m (dY/dX)"), 3, 0)
        self._slope_spin = self._spin(-1.0, 1.0, 0.0, "")
        self._slope_spin.setDecimals(4)
        self._slope_spin.setSingleStep(0.001)
        self._slope_spin.setEnabled(False)
        auto_layout.addWidget(self._slope_spin, 3, 1)
        self._scenario_tilted_rb.toggled.connect(self._slope_spin.setEnabled)

        self._auto_camera_btn = touch_button("OTOMATİK KAMERAYI BAŞLAT", primary=True, checkable=True)
        self._auto_camera_btn.toggled.connect(self._on_auto_camera_toggled)
        auto_layout.addWidget(self._auto_camera_btn, 4, 0, 1, 2)
        root.addWidget(auto_box)

        packet_box = QGroupBox("Manuel Tek Paket (otomatik kamera aktifken pasif)")
        packet_layout = QGridLayout(packet_box)
        self._target_x = self._spin(-100.0, 5000.0, 0.0, " mm")
        self._target_y = self._spin(-100.0, 100.0, 0.0, " mm")
        self._confidence_enabled = QCheckBox("Confidence gönder")
        self._confidence = self._spin(0.0, 1.0, 1.0, "")
        self._vision_ready_cb = QCheckBox("VisionReady")
        self._line_valid_cb = QCheckBox("LineValid")
        self._vision_fault_cb = QCheckBox("VisionFault")
        packet_layout.addWidget(QLabel("Hedef X (mm)"), 0, 0)
        packet_layout.addWidget(self._target_x, 0, 1)
        packet_layout.addWidget(QLabel("Hedef Y (mm)"), 1, 0)
        packet_layout.addWidget(self._target_y, 1, 1)
        packet_layout.addWidget(self._confidence_enabled, 2, 0)
        packet_layout.addWidget(self._confidence, 2, 1)
        packet_layout.addWidget(self._vision_ready_cb, 3, 0)
        packet_layout.addWidget(self._line_valid_cb, 3, 1)
        packet_layout.addWidget(self._vision_fault_cb, 4, 0)
        self._send_btn = touch_button("PAKET GÖNDER", primary=True)
        self._send_btn.clicked.connect(self._on_send_packet)
        packet_layout.addWidget(self._send_btn, 5, 0, 1, 2)
        root.addWidget(packet_box)

        hb_row = QHBoxLayout()
        self._heartbeat_cb = QCheckBox(
            "Heartbeat Otomatik Üret (manuel modda; otomatik kamerada kendisi yönetir)"
        )
        self._heartbeat_cb.toggled.connect(self._on_heartbeat_toggled)
        hb_row.addWidget(self._heartbeat_cb)
        root.addLayout(hb_row)

        op_box = QGroupBox("Ayrı Manuel Operatör Aksiyonları (otomatik kamera aktifken pasif)")
        op_layout = QHBoxLayout(op_box)
        self._cut_permit_cb = QCheckBox("CutPermit")
        self._cut_permit_cb.toggled.connect(self._on_cut_permit_toggled)
        self._z_down_cb = QCheckBox("ZDownRequest (bıçak indirme talebi)")
        self._z_down_cb.toggled.connect(self._on_z_down_toggled)
        op_layout.addWidget(self._cut_permit_cb)
        op_layout.addWidget(self._z_down_cb)
        root.addWidget(op_box)

        diag_box = QGroupBox("Salt Okunur Teşhis (PLC nihai otoritedir)")
        diag_layout = QGridLayout(diag_box)
        self._diag_labels: dict[str, QLabel] = {}
        for row, key in enumerate(
            [
                "auto_camera_status",
                "sensor_hint",
                "cycle_state",
                "cycle_active",
                "actual_xy",
                "servo_ready",
                "machine_ready_start_permitted",
                "trajectory",
                "vision_heartbeat_ok",
                "last_target",
                "last_sequence_heartbeat",
                "freshness",
            ]
        ):
            label = QLabel("—")
            label.setFont(base_font(10))
            label.setWordWrap(True)
            diag_layout.addWidget(label, row, 0)
            self._diag_labels[key] = label
        root.addWidget(diag_box, stretch=1)

    def _spin(self, lo: float, hi: float, default: float, suffix: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(lo, hi)
        spin.setDecimals(3)
        spin.setValue(default)
        if suffix:
            spin.setSuffix(suffix)
        return spin

    # -- arm/disarm -----------------------------------------------------------

    def _on_arm_clicked(self) -> None:
        ok, reason = self._sim.arm()
        if not ok:
            QMessageBox.warning(self, "ARM Edilemedi", reason)
        self._refresh_armed_ui()

    def _on_disarm_clicked(self) -> None:
        self._heartbeat_cb.setChecked(False)
        ok, note = self._sim.disarm()
        if note:
            QMessageBox.warning(self, "Disarm — Uyarı", note)
        self._refresh_armed_ui()

    def _on_armed_changed(self, _armed: bool) -> None:
        if not self._sim.armed:
            self._heartbeat_cb.blockSignals(True)
            self._heartbeat_cb.setChecked(False)
            self._cut_permit_cb.blockSignals(True)
            self._cut_permit_cb.setChecked(False)
            self._z_down_cb.blockSignals(True)
            self._z_down_cb.setChecked(False)
            self._auto_camera_btn.blockSignals(True)
            self._auto_camera_btn.setChecked(False)
            self._heartbeat_cb.blockSignals(False)
            self._cut_permit_cb.blockSignals(False)
            self._z_down_cb.blockSignals(False)
            self._auto_camera_btn.blockSignals(False)
        self._refresh_armed_ui()

    def _on_auto_camera_toggled(self, checked: bool) -> None:
        if checked:
            scenario = "tilted" if self._scenario_tilted_rb.isChecked() else "straight"
            ok, reason = self._sim.set_camera_scenario(scenario, self._slope_spin.value())
            if not ok:
                self._auto_camera_btn.blockSignals(True)
                self._auto_camera_btn.setChecked(False)
                self._auto_camera_btn.blockSignals(False)
                QMessageBox.warning(self, "Senaryo Reddedildi", reason)
                return
            ok, reason = self._sim.start_auto_camera(period_ms=self._auto_period_spin.value())
            if not ok:
                self._auto_camera_btn.blockSignals(True)
                self._auto_camera_btn.setChecked(False)
                self._auto_camera_btn.blockSignals(False)
                QMessageBox.warning(self, "Otomatik Kamera Başlatılamadı", reason)
                return
            self._auto_camera_btn.setText("OTOMATİK KAMERAYI DURDUR")
        else:
            self._sim.stop_auto_camera()
            self._auto_camera_btn.setText("OTOMATİK KAMERAYI BAŞLAT")
        self._refresh_armed_ui()

    def _on_auto_camera_changed(self, active: bool) -> None:
        # Servis kendi kendine durdurduysa (disarm/reconnect) butonu senkron
        # tut - kullanıcı tıklamadan da state değişebilir.
        self._auto_camera_btn.blockSignals(True)
        self._auto_camera_btn.setChecked(active)
        self._auto_camera_btn.blockSignals(False)
        self._auto_camera_btn.setText(
            "OTOMATİK KAMERAYI DURDUR" if active else "OTOMATİK KAMERAYI BAŞLAT"
        )
        # Heartbeat artık otomatik kameranın kendisi tarafından yönetiliyor
        # (2026-09-17 düzeltmesi) - kutu bu modda salt-gösterge, gerçek
        # `heartbeat_active` durumunu senkron göster.
        self._heartbeat_cb.blockSignals(True)
        self._heartbeat_cb.setChecked(self._sim.heartbeat_active)
        self._heartbeat_cb.blockSignals(False)
        self._refresh_armed_ui()

    def _refresh_armed_ui(self) -> None:
        armed = self._sim.armed
        auto_active = self._sim.auto_camera_active
        self._source_label.setText(f"Kaynak: {self._sim.source}")
        self._armed_label.setText("Durum: ARMED" if armed else "Durum: DISARMED")
        restyle(self._armed_label, 
            f"color: {COLORS['success'] if armed else COLORS['text_muted']}; font-weight: 600;"
        )
        self._arm_btn.setEnabled(not armed)
        self._disarm_btn.setEnabled(armed)

        self._auto_camera_btn.setEnabled(armed)
        self._auto_period_spin.setEnabled(armed and not auto_active)
        self._scenario_straight_rb.setEnabled(armed and not auto_active)
        self._scenario_tilted_rb.setEnabled(armed and not auto_active)
        self._slope_spin.setEnabled(armed and not auto_active and self._scenario_tilted_rb.isChecked())

        # Tek arbiter (görev notu): otomatik kamera aktifken manuel paket/
        # CutPermit/ZDownRequest kontrolleri PASİF - aynı tag'e zıt yazı
        # gitmesin. Heartbeat de otomatik kamera tarafından yönetilmiyor
        # ama otomatik kamerayla aynı armed oturumunu paylaştığı için
        # manuel bırakılabilir; karışıklığı önlemek için o da kilitleniyor.
        manual_enabled = armed and not auto_active
        for widget in (
            self._target_x,
            self._target_y,
            self._confidence_enabled,
            self._confidence,
            self._vision_ready_cb,
            self._line_valid_cb,
            self._vision_fault_cb,
            self._send_btn,
            self._heartbeat_cb,
            self._cut_permit_cb,
            self._z_down_cb,
        ):
            widget.setEnabled(manual_enabled)

    # -- packet / actions -----------------------------------------------------

    def _on_send_packet(self) -> None:
        confidence = self._confidence.value() if self._confidence_enabled.isChecked() else None
        ok, reason = self._sim.send_packet(
            target_x=self._target_x.value(),
            target_y=self._target_y.value(),
            vision_ready=self._vision_ready_cb.isChecked(),
            line_valid=self._line_valid_cb.isChecked(),
            vision_fault=self._vision_fault_cb.isChecked(),
            confidence=confidence,
        )
        if not ok:
            QMessageBox.warning(self, "Paket Gönderilemedi", reason)

    def _on_packet_result(self, ok: bool, message: str) -> None:
        if not ok:
            QMessageBox.warning(self, "Paket Başarısız", message or "PLC yazımı doğrulanamadı.")

    def _on_error(self, message: str) -> None:
        self._error_label.setText(f"Son yazma hatası: {message}")

    def _on_heartbeat_toggled(self, checked: bool) -> None:
        ok, reason = self._sim.set_heartbeat_enabled(checked)
        if not ok:
            self._heartbeat_cb.blockSignals(True)
            self._heartbeat_cb.setChecked(False)
            self._heartbeat_cb.blockSignals(False)
            QMessageBox.warning(self, "Heartbeat Başlatılamadı", reason)

    def _on_cut_permit_toggled(self, checked: bool) -> None:
        ok, reason = self._sim.send_cut_permit(checked)
        if not ok:
            self._cut_permit_cb.blockSignals(True)
            self._cut_permit_cb.setChecked(False)
            self._cut_permit_cb.blockSignals(False)
            QMessageBox.warning(self, "CutPermit Yazılamadı", reason)

    def _on_z_down_toggled(self, checked: bool) -> None:
        if checked:
            confirm = QMessageBox.question(
                self,
                "ZDownRequest Onayı",
                "Bıçak indirme talebi (ZDownRequest) gönderilecek. Onaylıyor musunuz?",
            )
            if confirm != QMessageBox.StandardButton.Yes:
                self._z_down_cb.blockSignals(True)
                self._z_down_cb.setChecked(False)
                self._z_down_cb.blockSignals(False)
                return
        ok, reason = self._sim.send_z_down_request(checked)
        if not ok:
            self._z_down_cb.blockSignals(True)
            self._z_down_cb.setChecked(False)
            self._z_down_cb.blockSignals(False)
            QMessageBox.warning(self, "ZDownRequest Yazılamadı", reason)

    # -- diagnostics ------------------------------------------------------------

    def _on_snapshot(self, snap: MachineSnapshot) -> None:
        d = self._diag_labels
        if self._sim.auto_camera_active:
            scenario_txt = "Eğimli" if self._sim.camera_scenario == "tilted" else "Düz Çizgi"
            target_txt = (
                f", son hedef X/Y: {self._sim.last_target_x:.2f}/{self._sim.last_target_y:.2f} mm"
                if self._sim.last_target_x is not None and self._sim.last_target_y is not None
                else ""
            )
            d["auto_camera_status"].setText(
                f"Otomatik Kamera: AKTİF ({scenario_txt}, periyot {self._sim.auto_camera_period_ms} ms){target_txt}"
            )
            restyle(d["auto_camera_status"], f"color: {COLORS['success']}; font-weight: 600;")
        else:
            d["auto_camera_status"].setText("Otomatik Kamera: KAPALI (manuel modda)")
            restyle(d["auto_camera_status"], f"color: {COLORS['text_muted']};")
        d["sensor_hint"].setText(f"Şimdi: {sensor_hint(snap.cycle_state)}")
        d["cycle_state"].setText(f"Durum: {cycle_state_label(snap.cycle_state)}")
        d["cycle_active"].setText(f"Çevrim Aktif: {snap.cycle_active} | Manuel: {snap.manual_mode}")
        d["actual_xy"].setText(f"Actual X/Y: {snap.x_actual_pos:.2f} / {snap.y_actual_pos:.2f} mm")
        d["servo_ready"].setText(
            f"Servo Hazır X/Y: {snap.x_servo_ready}/{snap.y_servo_ready} | MachineReady: {snap.machine_ready}"
        )
        d["machine_ready_start_permitted"].setText(
            f"StartPermitted: {snap.start_permitted} | ClampDown: {snap.clamp_down} | BladeDown: {snap.blade_down}"
        )
        d["trajectory"].setText(
            f"xTrajectoryValid: {snap.trajectory_valid} | xTrajectoryFault: {snap.trajectory_fault} | "
            f"lrMaxAllowedSlope: {snap.lr_max_allowed_slope:g}"
        )
        d["vision_heartbeat_ok"].setText(
            f"VisionReady: {snap.vision_ready} | LineValid: {snap.line_valid} | "
            f"VisionFault: {snap.vision_fault} | xVisionHeartbeatOK: {snap.vision_heartbeat_ok}"
        )
        d["last_target"].setText(
            f"PLC'deki TargetX/TargetY: {snap.vision_target_x:.2f} / {snap.vision_target_y:.2f} mm"
        )
        d["last_sequence_heartbeat"].setText(
            f"udiVisionSequence: {snap.vision_sequence} | Heartbeat: {snap.vision_heartbeat}"
        )
        conn = snap.connection_state
        stale_txt = " (STALE)" if snap.stale else ""
        self._conn_label.setText(f"Bağlantı: {conn}{stale_txt}")
        d["freshness"].setText("Veri güncel" if not snap.stale else "Veri STALE - yeni paket gönderilmez")

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # Sayfadan ayrılma: sahiplik ANINDA bırakılır. Çevrim aktifse
        # disarm() zaten izin alanlarını geri çekmeyip kullanıcıyı bilgilendirir.
        _ok, note = self._sim.disarm()
        if note:
            QMessageBox.warning(self, "Disarm — Uyarı", note)
        super().closeEvent(event)
