"""C8 — "Sıfır Referansı Belirle" (PLC-HMI-20260923-20, sade sürüm):
mevcut fiziksel X/Y konumunu 0 yapan, şifreli, uygulama genelinde MODAL bir
servis penceresi. Kaynak: `.ai/HMI_C8_SADE_SURUM_20260923.md`.

Görev talimatı (aynen): Manuel; bıçak/baskı yukarı; EMG bas; eksenleri elle
sıfıra getir; ellerini çek; EMG bırak; servolar hazır; tek düğmeye 3 saniye
bas. HMI EMG basış geçmişini İZLEMEZ (önceki, iptal edilen 19 numaralı
paketin 10 tag'lık sözleşmesinin aksine) - yalnız düğmeye basıldığı ANDAKİ
koşulları (`MachineService.set_zero_reference_allowed_now`) kontrol eder;
talimat metni operatöre gösterilir, PLC'nin kendi CFC AND zinciri esastır.

Modal pencere, işlem sürerken (`sent`/`busy`) normal yollarla (X düğmesi,
Esc, "Kapat") kapatılamaz - görev notu. Odak kaybı, uygulama pasifleşmesi
veya bağlantı bayatlaması 3 saniyelik basılı tutuşu iptal eder (ManualPage'
deki C5 "Başlangıç Konumuna Dön" ile aynı desen)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox, QVBoxLayout

from core.models import MachineSnapshot
from services.machine_service import MachineService
from ui.machine.theme import COLORS, base_font
from ui.machine.widgets import HoldButton, touch_button

HOLD_MS = 3000

_RESULT_TEXT = {
    "done": ("X ve Y sıfır referansı belirlendi.", "ok"),
    "error": (
        "Sıfırlama tamamlanamadı. X/Y blok hata bilgisini kontrol edin; "
        "iki eksenin referansını yeniden doğrulayın.",
        "fault",
    ),
}

_CONDITIONS_NOT_MET_TEXT = (
    "Sıfırlama koşulları sağlanmıyor. Manuel mod, servo hazır ve "
    "mekanizmaların yukarıda olduğunu kontrol edin."
)

_MOOD_COLOR = {
    "ok": "success",
    "warn": "warning",
    "fault": "danger",
    "inactive": "text_muted",
}


class SetZeroReferenceDialog(QDialog):
    def __init__(self, service: MachineService, parent=None):
        super().__init__(parent)
        self._service = service
        self._holding = False

        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._on_hold_complete)
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(100)
        self._progress_timer.timeout.connect(self._update_progress)

        self.setWindowTitle("Sıfır Referansı Belirle")
        self.setModal(True)
        self.resize(520, 420)
        self._build_ui()

        service.snapshotUpdated.connect(self._on_snapshot)
        service.commandWriteError.connect(self._on_command_write_error)
        app = QApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._on_application_state_changed)

        self._on_snapshot(service.snapshot)

    # -- layout ---------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("SIFIR REFERANSI BELİRLE")
        title.setFont(base_font(13, bold=True))
        layout.addWidget(title)

        instructions = QLabel(
            "1. Manuel modda olduğunuzdan, bıçak ve baskının YUKARIDA "
            "olduğundan emin olun.\n"
            "2. ACİL DURDUR'a basın.\n"
            "3. Eksenleri elle istediğiniz sıfır konumuna getirin.\n"
            "4. Ellerinizi mekanizmalardan çekin.\n"
            "5. ACİL DURDUR'u bırakın; servoların hazır olmasını bekleyin.\n"
            "6. Aşağıdaki düğmeyi 3 saniye basılı tutun."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self._condition_label = QLabel()
        self._condition_label.setWordWrap(True)
        layout.addWidget(self._condition_label)

        self._button = HoldButton("BU KONUMU X=0 / Y=0 YAP")
        self._button.setMinimumHeight(80)
        self._button.held.connect(self._on_held)
        layout.addWidget(self._button)

        self._hint_label = QLabel("3 saniye basılı tutun")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self._hint_label)

        self._result_label = QLabel()
        self._result_label.setWordWrap(True)
        layout.addWidget(self._result_label)

        layout.addStretch(1)

        self._close_btn = touch_button("Kapat")
        self._close_btn.clicked.connect(self.close)
        layout.addWidget(self._close_btn)

    # -- lifecycle / modal-close guard -----------------------------------

    def _busy(self) -> bool:
        return self._service.set_zero_status() in ("sent", "busy")

    def reject(self) -> None:  # noqa: N802 (Qt override) - Esc / programmatic
        if self._busy():
            return
        super().reject()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override) - title-bar X
        if self._busy():
            event.ignore()
            return
        self._teardown()
        super().closeEvent(event)

    def _teardown(self) -> None:
        self._cancel_hold()
        app = QApplication.instance()
        if app is not None:
            try:
                app.applicationStateChanged.disconnect(self._on_application_state_changed)
            except (TypeError, RuntimeError):
                pass
        try:
            self._service.snapshotUpdated.disconnect(self._on_snapshot)
            self._service.commandWriteError.disconnect(self._on_command_write_error)
        except (TypeError, RuntimeError):
            pass

    def _on_application_state_changed(self, state: Qt.ApplicationState) -> None:
        if state != Qt.ApplicationState.ApplicationActive:
            self._cancel_hold()

    # -- 3 saniyelik basılı tutuş -----------------------------------------

    def _on_held(self, active: bool) -> None:
        if active:
            self._start_hold()
        else:
            self._cancel_hold()

    def _start_hold(self) -> None:
        if self._holding:
            return
        if not self._service.set_zero_reference_allowed_now():
            return
        self._holding = True
        self._hold_timer.start(HOLD_MS)
        self._progress_timer.start()
        self._update_progress()

    def _cancel_hold(self) -> None:
        # Erken bırakma, odak/uygulama kaybı, bağlantı bayatlaması, pencere
        # kapanışı - hepsi buraya düşer. Sayaç tam sıfırlanır; bir sonraki
        # deneme YENİ, baştan bir basış ister.
        if not self._holding:
            return
        self._holding = False
        self._hold_timer.stop()
        self._progress_timer.stop()
        self._hint_label.setText("3 saniye basılı tutun")

    def _update_progress(self) -> None:
        remaining_ms = self._hold_timer.remainingTime()
        if remaining_ms < 0:
            return
        self._hint_label.setText(f"Basılı tutun… {remaining_ms / 1000:.1f}s")

    def _on_hold_complete(self) -> None:
        self._progress_timer.stop()
        self._holding = False
        if not self._service.request_set_zero():
            # Basılı tutuş sürerken koşullar bozulmuş olabilir - talep hiç
            # gönderilmedi, operatöre AÇIKÇA söylenir (sessizce yutulmaz).
            QMessageBox.warning(self, "Reddedildi", _CONDITIONS_NOT_MET_TEXT)
            self._hint_label.setText("3 saniye basılı tutun")
            return
        self._hint_label.setText("")

    # -- data binding -------------------------------------------------------

    def _on_snapshot(self, snap: MachineSnapshot) -> None:
        status = self._service.set_zero_status()

        if self._holding and not self._service.set_zero_reference_allowed_now():
            self._cancel_hold()

        ready = self._service.set_zero_reference_allowed_now()
        busy = status in ("sent", "busy")
        tags_configured = self._service.set_zero_tags_configured()

        if not tags_configured:
            # PLC-HMI-20260923-22 (kullanıcı bulgusu, gerçek PLC testi):
            # tag'ler config'te olmadığı sürece `ready` HER ZAMAN False -
            # eskiden bu durumda da genel "koşullar sağlanmıyor" metni
            # gösteriliyordu, operatörü kendi manuel/servo kurulumunu
            # sorgulamaya yönlendiriyordu. Gerçek sebep (PLC henüz online
            # doğrulamadı) artık AÇIKÇA söyleniyor (TAG EKSİK deseni,
            # ManualPage'deki C5 ile aynı disiplin).
            self._condition_label.setText(
                "TAG EKSİK - PLC bu özelliğin tag'lerini (xSetZeroRequest, "
                "MC_Home_X/MC_Home_Y durum alanları) henüz online "
                "doğrulamadı. Sıfırlama, PLC tarafı tamamlanıp gerçek "
                "config'e eklenene kadar kullanılamaz - bu sizin makine "
                "kurulumunuzdan kaynaklanmıyor."
            )
            self._condition_label.setStyleSheet(f"color: {COLORS['danger']};")
        elif snap.stale and busy:
            self._condition_label.setText(
                "Bağlantı kesildi - sonuç belirsiz. Bağlantı geri gelince "
                "güncel durum okunacak; talep otomatik tekrar gönderilmeyecek."
            )
            self._condition_label.setStyleSheet(f"color: {COLORS['warning']};")
        elif busy:
            self._condition_label.setText("İşlem sürüyor - bekleyin.")
            self._condition_label.setStyleSheet(f"color: {COLORS['warning']};")
        elif ready:
            self._condition_label.setText("Koşullar sağlanıyor.")
            self._condition_label.setStyleSheet(f"color: {COLORS['success']};")
        else:
            self._condition_label.setText(_CONDITIONS_NOT_MET_TEXT)
            self._condition_label.setStyleSheet(f"color: {COLORS['warning']};")

        self._button.setEnabled(ready and not busy)

        if status in _RESULT_TEXT:
            text, mood = _RESULT_TEXT[status]
            if status == "error":
                error_id = snap.x_home_error_id or snap.y_home_error_id
                if error_id:
                    text = f"{text} (HataID: {error_id})"
            self._result_label.setText(text)
            self._result_label.setStyleSheet(f"color: {COLORS[_MOOD_COLOR[mood]]};")
        else:
            self._result_label.setText("")

        self._close_btn.setEnabled(not busy)

    def _on_command_write_error(self, tag: str, reason: str) -> None:
        if tag != "cmd_set_zero_request":
            return
        QMessageBox.warning(
            self,
            "Yazma Reddedildi",
            f"Sıfırlama talebi PLC tarafından reddedildi.\n\nGerçek OPC UA hatası:\n{reason}",
        )
