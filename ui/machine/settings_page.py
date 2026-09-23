"""Screen C — Ayarlar / Mühendislik ekranı (integration brief section 8-C,
13, 24). Kept separate from the operator screen; parameter edits require an
explicit "Mühendislik Erişimi" unlock plus a confirmation dialog per edit,
since these are mechanical/motion limits (brief section 8: "Kritik mekanik
parametrelerin yanlışlıkla değiştirilmemesi için confirmation ...").

2026-09-16: the parameter list itself must never show a fabricated
default as if it were the real PLC value — every row starts disabled and
shows "Okunuyor…" until `MachineService.is_parameter_confirmed()` says a
real read has come back (always true instantly in Demo mode); after that,
the row stays live-synced from the snapshot tick unless the user has
edited it (tracked via a "dirty" flag, NOT `spin.hasFocus()`): clicking
"Uygula" moves keyboard focus to the button on mouse-press, before the
click even fires, so a focus-based guard let the 50ms live-sync tick win
that race and silently revert the just-typed value before Apply ever saw
it (real-PLC bug report). The dirty flag is set only by genuine user edits
(`valueChanged`, disabled while we set the value ourselves) and is only
cleared once a write is confirmed or fails."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.models import MachineSnapshot
from core.parameters import PARAMETER_SPECS
from services.machine_service import MachineService
from services.vision_simulator import VisionSimulatorService
from ui.machine.set_zero_dialog import SetZeroReferenceDialog
from ui.machine.theme import COLORS, base_font
from ui.machine.vision_simulator_page import VisionSimulatorDialog
from ui.machine.widgets import touch_button

# Kullanıcı talebi (2026-09-18): Vision simülatörü butonuna ek bir şifre
# kapısı - Mühendislik Erişimi zaten açık olsa bile, HER açılışta (pencere
# kapatılıp tekrar açılsa dahi) yeniden sorulur; hiçbir yerde önbelleğe
# alınmaz. Kaynak kodda düz metin - gerçek bir güvenlik sınırı değil, kazara
# tıklamaya karşı ek bir engel (görev notu: hard-coded parola tek başına
# "yetki" sayılmaz, bu yüzden Mühendislik Erişimi kapısı da korunuyor).
# PLC-HMI-20260923-20 (C8): "Sıfır Referansı Belirle" de AYNI şifreyi
# kullanır (görev notu: "mevcut mühendislik şifresi") - ayrı bir parola
# icat edilmedi.
VISION_SIM_PASSWORD = "90327"

# Kullanıcı isteği (2026-09-23): Ayarlar tablosundaki her satır aynı,
# ölçülü yükseklikte olsun - "Etki" özeti satırı büyütmesin diye tek satıra
# sığdırılıp (elided) tam metin yalnız tooltip'te gösterilir.
_PARAM_ROW_HEIGHT = 32
_EFFECT_LABEL_MAX_WIDTH = 220


def _elided_text(text: str, max_width: int) -> str:
    metrics = QFontMetrics(base_font(10))
    return metrics.elidedText(text, Qt.TextElideMode.ElideRight, max_width)


class SettingsPage(QWidget):
    def __init__(self, service: MachineService, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = service
        self._unlocked = False
        self._confirmed_shown: set[str] = set()
        self._dirty: set[str] = set()  # keys with a genuine unsaved user edit
        # key -> (spin, apply_btn, status_label)
        self._rows: dict[str, tuple[QDoubleSpinBox, QPushButton, QLabel]] = {}
        # Geçici Vision simülatörü (PLC-HMI-20260917-02): tembel oluşturulur,
        # tekil (aynı pencere tekrar açılıp getirilir - "aynı HMI içinde iki
        # simülatör oturumunu önle" görev notu).
        self._vision_sim: VisionSimulatorService | None = None
        self._vision_dialog: VisionSimulatorDialog | None = None
        # 2026-09-18 bug report: "HATA — PLC onaylamadı" gerçek OPC UA
        # sebebini gizliyordu. Bir yazma gerçekten reddedilirse (BadXxx),
        # gerçek sebep burada tutulup _on_write_failed'de gösterilir.
        self._param_last_error: dict[str, str] = {}
        self._build_ui()
        service.snapshotUpdated.connect(self._on_snapshot)
        service.parameterWriteConfirmed.connect(self._on_write_confirmed)
        service.parameterWriteFailed.connect(self._on_write_failed)
        service.parameterWriteError.connect(self._on_write_error)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("AYARLAR / MÜHENDİSLİK")
        title.setFont(base_font(14, bold=True))
        header.addWidget(title)
        header.addStretch(1)
        # Geçici Vision simülatörü giriş noktası: yalnız feature flag açık
        # VE Mühendislik Erişimi açıkken görünür - ayrı gizli menü/parola
        # değil, mevcut yetki kapısı yeniden kullanılıyor (görev, Faz 1).
        self._vision_sim_btn = touch_button("VISION SİMÜLATÖR ⚙", object_name="navButton")
        self._vision_sim_btn.setVisible(self._service.vision_simulator_enabled)
        self._vision_sim_btn.setEnabled(False)
        self._vision_sim_btn.clicked.connect(self._open_vision_simulator)
        header.addWidget(self._vision_sim_btn)
        # PLC-HMI-20260923-20 (C8, sade sürüm): aynı yetki deseni yeniden
        # kullanılır - Mühendislik Erişimi AÇIK olmalı, ayrıca her açılışta
        # şifre. Eksik HMI eşlemesi varken (bkz. tooltip) içerideki düğme
        # bunu açıkça gösterir - buton kendisi görünür/tıklanabilir kalır
        # (bu bir nadir kullanılan servis penceresi - ana ekran göstergesi
        # değil, o yüzden ayrı bir "eksik" rozeti gerekmedi).
        self._set_zero_btn = touch_button("SIFIR REFERANSI BELİRLE ⚙", object_name="navButton")
        self._set_zero_btn.setEnabled(False)
        if not self._service.set_zero_tags_configured():
            # PLC-HMI-20260923-23 (düzeltme): "PLC henüz online doğrulamadı"
            # demek, PLC'nin kodu yüklemediğini ima ediyordu - salt-okunur
            # browse'la `xSetZeroRequest`'in canlı olduğu doğrulandı, yalnız
            # HMI eşlemesi (Symbol Configuration'da yayınlanmamış 10 FB
            # üyesi) eksik. Metin bunu net ayırıyor.
            self._set_zero_btn.setToolTip(
                "HMI bağlantı ayarında sıfırlama alanları eksik: "
                + ", ".join(self._service.set_zero_missing_tags())
            )
        self._set_zero_btn.clicked.connect(self._open_set_zero_dialog)
        header.addWidget(self._set_zero_btn)
        root.addLayout(header)

        warning = QFrame()
        warning.setObjectName("card")
        warning_layout = QHBoxLayout(warning)
        warning_label = QLabel(
            "⚠ MÜHENDİSLİK ALANI — Bu parametreler makinenin mekanik hareket "
            "limitlerini belirler. Yanlış değer ekipmana zarar verebilir."
        )
        warning_label.setStyleSheet(f"color: {COLORS['warning']};")
        warning_label.setWordWrap(True)
        self._unlock_checkbox = QCheckBox("Mühendislik Erişimini Aç")
        # Kullanıcı isteği (2026-09-23): QCheckBox global QWidget kuralından
        # (page_bg arka plan) dolayı çevresindeki kartın (navy) üzerinde
        # sırıtan bir dikdörtgen gösteriyordu - arka plan şeffaf yapıldı; yazı
        # rengi yanındaki uyarı metniyle aynı (uyarı rengi).
        self._unlock_checkbox.setStyleSheet(f"background: transparent; color: {COLORS['warning']};")
        self._unlock_checkbox.toggled.connect(self._on_unlock_toggled)
        warning_layout.addWidget(warning_label, stretch=1)
        warning_layout.addWidget(self._unlock_checkbox)
        root.addWidget(warning)

        root.addWidget(self._build_opcua_card())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        param_widget = QWidget()
        grid = QGridLayout(param_widget)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        grid.addWidget(self._header_label("Parametre"), 0, 0)
        grid.addWidget(self._header_label("Değer"), 0, 1)
        grid.addWidget(self._header_label("Birim"), 0, 2)
        grid.addWidget(self._header_label("Sınır"), 0, 3)
        grid.addWidget(self._header_label(""), 0, 4)
        # Kullanıcı isteği (2026-09-23): "Etki ile Durum sütununu yer
        # değiştir, Durum sayfanın boşluğunu alsın" - Etki (kısa, tek
        # satırlık özet) dar sütunda (5), Durum (büyüyebilen) en sonda (6).
        grid.addWidget(self._header_label("Etki"), 0, 5)
        grid.addWidget(self._header_label("Durum"), 0, 6)
        # Kullanıcı isteği (2026-09-23): Uygula butonları küçüldü, boşalan
        # yer Etki/Durum sütunlarına gitsin (gerekirse büyüsünler); diğer
        # sütunlar sabit kalır - tüm satırlar simetrik/aynı boyutta.
        # DÜZELTME (2026-09-23, ekran görüntüsü): "Parametre" sütununa
        # stretch verilince isim ile Değer arasında büyük boş alan
        # oluşuyordu - o boşluk hiç dağıtılmıyor (0), fazlası Durum'a gidiyor.
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(5, 1)
        grid.setColumnStretch(6, 3)

        for row_index, spec in enumerate(PARAMETER_SPECS, start=1):
            name_label = QLabel(spec.label_tr)
            spin = QDoubleSpinBox()
            spin.setRange(spec.min_value, spec.max_value)
            spin.setDecimals(2)
            spin.setValue(self._service.get_parameter_value(spec.key))
            spin.setEnabled(False)
            spin.setFixedHeight(_PARAM_ROW_HEIGHT)
            # Only fires for a genuine user edit: our own live-sync/initial
            # setValue calls below are wrapped in blockSignals().
            spin.valueChanged.connect(lambda _v, key=spec.key: self._dirty.add(key))
            unit_label = QLabel(spec.unit)
            unit_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            limit_label = QLabel(f"{spec.min_value:g} — {spec.max_value:g}")
            limit_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            apply_btn = QPushButton("Uygula")
            apply_btn.setObjectName("applyButtonSmall")
            apply_btn.setFixedSize(84, _PARAM_ROW_HEIGHT)
            apply_btn.setEnabled(False)
            status_label = QLabel("")
            effect_label = QLabel(_elided_text(spec.effect_tr, _EFFECT_LABEL_MAX_WIDTH))
            effect_label.setWordWrap(False)
            effect_label.setToolTip(spec.effect_tr)
            effect_label.setStyleSheet(f"color: {COLORS['text_secondary']};")

            apply_btn.clicked.connect(
                lambda _checked=False, key=spec.key, box=spin, label=status_label, spec_=spec: self._apply_parameter(
                    key, box, label, spec_
                )
            )

            grid.addWidget(name_label, row_index, 0)
            grid.addWidget(spin, row_index, 1)
            grid.addWidget(unit_label, row_index, 2)
            grid.addWidget(limit_label, row_index, 3)
            grid.addWidget(apply_btn, row_index, 4)
            grid.addWidget(effect_label, row_index, 5)
            grid.addWidget(status_label, row_index, 6)

            self._rows[spec.key] = (spin, apply_btn, status_label)
            if not self._service.is_parameter_confirmed(spec.key):
                status_label.setText("Okunuyor…")
                status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            else:
                self._confirmed_shown.add(spec.key)

        scroll.setWidget(param_widget)
        root.addWidget(scroll, stretch=1)

    def _header_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(base_font(10, bold=True))
        label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        return label

    def _build_opcua_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QHBoxLayout(card)
        layout.addWidget(QLabel("OPC UA Endpoint:"))
        self._endpoint_edit = QLineEdit(self._service.endpoint)
        self._endpoint_edit.setEnabled(False)
        layout.addWidget(self._endpoint_edit, stretch=1)
        self._endpoint_save_btn = touch_button("Kaydet (Yeniden Başlatma Gerekir)")
        self._endpoint_save_btn.setEnabled(False)
        self._endpoint_save_btn.clicked.connect(self._save_endpoint)
        # Kullanıcı isteği (2026-09-23): IP kutusu butondan ince/asimetrik
        # duruyordu - ikisine de eşit stretch verilince boşluğu eşit paylaşıp
        # aynı büyüklükte görünürler.
        layout.addWidget(self._endpoint_save_btn, stretch=1)
        return card

    # -- data binding ---------------------------------------------------------

    def _on_snapshot(self, snap: MachineSnapshot) -> None:
        # Güvenlik (2026-09-16, kullanıcı isteği): makine xCycleActive iken
        # (otomatik çevrimde) Mühendislik erişimi açık kalamaz - çevrim
        # ortasında biri unlock alip devam ederse zorla kilitlenir.
        # `self._unlocked` HEMEN False yapılıyor ki bloklayan uyarı
        # penceresi sırasında gelecek bir sonraki tick tekrar tetiklemesin.
        #
        # ÖNEMLİ (2026-09-17, kullanıcı düzeltmesi): bu kilit yalnız
        # MEKANİK PARAMETRE düzenlemesini (yukarıdaki satırlar) kapatır.
        # Zaten ARMED olan Vision simülatörü penceresini KAPATMAZ/disarm
        # ETMEZ - aracın tüm amacı, operatör otomatik çevrimi başlattığında
        # (tam olarak bu an: cycle_active TRUE olduğu an) kamera verisini
        # PLC'ye beslemeye devam etmesidir ("otomatik programı
        # başlattığımda kameradan gerekli veriler gelecek"). Yalnız YENİ
        # bir simülatör penceresi açmayı engeller (buton devre dışı).
        if snap.cycle_active and self._unlocked:
            self._unlocked = False
            self._unlock_checkbox.blockSignals(True)
            self._unlock_checkbox.setChecked(False)
            self._unlock_checkbox.blockSignals(False)
            for key in self._rows:
                self._update_row_enabled(key)
            self._endpoint_edit.setEnabled(False)
            self._endpoint_save_btn.setEnabled(False)
            self._vision_sim_btn.setEnabled(False)
            self._set_zero_btn.setEnabled(False)
            vision_note = (
                " Açık olan Vision simülatör penceresi kapanmadı, beslemeye "
                "devam edebilirsiniz."
                if self._vision_dialog is not None and self._vision_dialog.isVisible()
                else ""
            )
            QMessageBox.warning(
                self,
                "Erişim Kapatıldı",
                "Makine otomatik çevrime girdi. Mühendislik erişimi (parametre "
                "düzenleme) güvenlik nedeniyle kapatıldı." + vision_note,
            )

        for spec in PARAMETER_SPECS:
            spin, _apply_btn, status_label = self._rows[spec.key]

            if spec.key not in self._confirmed_shown and self._service.is_parameter_confirmed(spec.key):
                self._confirmed_shown.add(spec.key)
                status_label.setText("")
                status_label.setStyleSheet("")
                self._update_row_enabled(spec.key)

            # Live-sync from the PLC; never fight a genuine unsaved user
            # edit (dirty flag, not hasFocus() - see module docstring).
            if spec.key in self._confirmed_shown and spec.key not in self._dirty:
                value = self._service.get_parameter_value(spec.key)
                if abs(spin.value() - value) > 1e-9:
                    spin.blockSignals(True)
                    spin.setValue(value)
                    spin.blockSignals(False)

    # -- interactions ---------------------------------------------------------

    def _row_enabled(self, key: str) -> bool:
        return self._unlocked and key in self._confirmed_shown

    def _update_row_enabled(self, key: str) -> None:
        spin, apply_btn, _status_label = self._rows[key]
        enabled = self._row_enabled(key)
        spin.setEnabled(enabled)
        apply_btn.setEnabled(enabled)

    def _on_unlock_toggled(self, checked: bool) -> None:
        if checked and self._service.snapshot.cycle_active:
            self._unlock_checkbox.blockSignals(True)
            self._unlock_checkbox.setChecked(False)
            self._unlock_checkbox.blockSignals(False)
            QMessageBox.warning(
                self,
                "Erişim Reddedildi",
                "Makine otomatik çevrimde çalışırken Mühendislik ayarlarına "
                "erişilemez.\nAyarları değiştirmek için önce çevrimi durdurun.",
            )
            return
        self._unlocked = checked
        for key in self._rows:
            self._update_row_enabled(key)
        self._endpoint_edit.setEnabled(checked)
        self._endpoint_save_btn.setEnabled(checked)
        self._vision_sim_btn.setEnabled(checked and self._service.vision_simulator_enabled)
        self._set_zero_btn.setEnabled(checked)
        if not checked:
            self._close_vision_simulator()

    def _apply_parameter(self, key: str, spin: QDoubleSpinBox, status_label: QLabel, spec) -> None:
        value = spin.value()
        confirm = QMessageBox.question(
            self,
            "Parametre Değişikliği Onayı",
            f"{spec.label_tr} değeri {value:g} {spec.unit} olarak ayarlanacak.\nOnaylıyor musunuz?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._param_last_error.pop(key, None)
        try:
            self._service.set_parameter(key, value)
        except ValueError as exc:
            QMessageBox.warning(self, "Geçersiz Değer", str(exc))
            status_label.setText("HATA")
            status_label.setStyleSheet(f"color: {COLORS['danger']};")
            return
        # Do NOT claim success yet - wait for the PLC to actually echo the
        # written value back (or time out). A premature "✓ UYGULANDI" here
        # was masking real write failures (2026-09-16 real-PLC bug report):
        # the next 100ms read tick would silently revert the value while the
        # status label kept saying it worked.
        status_label.setText("Yazılıyor…")
        status_label.setStyleSheet(f"color: {COLORS['text_muted']};")

    def _on_write_confirmed(self, key: str) -> None:
        row = self._rows.get(key)
        if row is None:
            return
        _spin, _apply_btn, status_label = row
        self._dirty.discard(key)
        self._param_last_error.pop(key, None)
        status_label.setText("✓ UYGULANDI")
        status_label.setStyleSheet(f"color: {COLORS['success']};")

    def _on_write_error(self, key: str, reason: str) -> None:
        """2026-09-18 bug report: jenerik "PLC onaylamadı" mesajı gerçek OPC
        UA reddini gizliyordu. `MachineService._on_error`, bekleyen bir
        parametre yazmasıyla eşleşen gerçek bir OPC UA hatası görürse bunu
        buraya taşır - `_on_write_failed` (timeout sonrası) bunu gösterir."""
        self._param_last_error[key] = reason

    def _on_write_failed(self, key: str) -> None:
        row = self._rows.get(key)
        if row is None:
            return
        _spin, _apply_btn, status_label = row
        self._dirty.discard(key)
        reason = self._param_last_error.pop(key, None)
        if reason:
            # Gerçek bir OPC UA yazma hatası vardı (örn. BadUserAccessDenied,
            # BadOutOfRange) - bunu göster, salt "onaylamadı" değil.
            status_label.setText("HATA — PLC yazmayı reddetti")
            status_label.setToolTip(reason)
            QMessageBox.warning(
                self,
                "Yazma Reddedildi",
                f"PLC bu değeri kabul etmedi.\n\nGerçek OPC UA hatası:\n{reason}",
            )
        else:
            # Gerçek bir OPC UA hatası görülmedi - yazma muhtemelen kabul
            # edildi ama okuma hiç yazılan değeri yansıtmadı (örn. PLC
            # mantığı değeri kendi hesabıyla geri yazıyor olabilir).
            status_label.setText("HATA — PLC onaylamadı")
            status_label.setToolTip(
                "Yazma sırasında OPC UA hatası görülmedi; olası neden: PLC "
                "değeri kendi mantığıyla geri değiştiriyor."
            )
        status_label.setStyleSheet(f"color: {COLORS['danger']};")

    def _open_vision_simulator(self) -> None:
        if not self._unlocked or not self._service.vision_simulator_enabled:
            return
        if not self._prompt_vision_sim_password():
            return
        if self._vision_sim is None:
            self._vision_sim = VisionSimulatorService(self._service, self)
        if self._vision_dialog is None:
            self._vision_dialog = VisionSimulatorDialog(self._vision_sim, self._service, self)
        # Aynı HMI içinde iki simülatör penceresi açılmasını önle: var olanı
        # öne getir (görev notu, Faz 1).
        self._vision_dialog.show()
        self._vision_dialog.raise_()
        self._vision_dialog.activateWindow()

    def _prompt_vision_sim_password(self) -> bool:
        """Her açılışta sorulur - pencere kapatılıp tekrar açılsa, hatta
        aynı oturumda birden fazla kez açılsa dahi (kullanıcı talebi,
        2026-09-18); hiçbir yerde "bu oturumda zaten girildi" önbelleği
        tutulmaz."""
        text, ok = QInputDialog.getText(
            self,
            "Mühendislik Şifresi",
            "Vision simülatörünü açmak için 5 haneli şifreyi girin:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return False
        if text != VISION_SIM_PASSWORD:
            QMessageBox.warning(self, "Şifre Hatalı", "Girilen şifre yanlış.")
            return False
        return True

    def _open_set_zero_dialog(self) -> None:
        """PLC-HMI-20260923-20 (C8, sade sürüm): "Ayarlarda her açılışta
        şifre, uygulama genelinde MODAL popup" - Vision simülatöründen
        farklı olarak (armed/canlı besleme, tekil pencere) burada her
        açılış TAMAMEN yeni bir diyalog; önbelleğe alınan bir örnek yok."""
        if not self._unlocked:
            return
        if not self._prompt_set_zero_password():
            return
        dialog = SetZeroReferenceDialog(self._service, self)
        dialog.exec()

    def _prompt_set_zero_password(self) -> bool:
        """Vision simülatörüyle AYNI mühendislik şifresi - her açılışta
        yeniden sorulur, hiçbir yerde önbelleğe alınmaz (görev notu)."""
        text, ok = QInputDialog.getText(
            self,
            "Mühendislik Şifresi",
            "Sıfır Referansı Belirle'yi açmak için 5 haneli şifreyi girin:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return False
        if text != VISION_SIM_PASSWORD:
            QMessageBox.warning(self, "Şifre Hatalı", "Girilen şifre yanlış.")
            return False
        return True

    def _close_vision_simulator(self) -> None:
        if self._vision_dialog is not None:
            self._vision_dialog.close()  # closeEvent() zaten disarm() çağırır
        elif self._vision_sim is not None:
            self._vision_sim.disarm()

    def _save_endpoint(self) -> None:
        endpoint = self._endpoint_edit.text().strip()
        self._service.update_endpoint(endpoint)
        QMessageBox.information(
            self,
            "Kaydedildi",
            "OPC UA endpoint kaydedildi. Değişikliğin etkili olması için uygulamayı yeniden başlatın.",
        )
