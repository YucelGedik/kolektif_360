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

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
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
from ui.machine.theme import COLORS, base_font
from ui.machine.widgets import touch_button


class SettingsPage(QWidget):
    navigateRequested = Signal(str)  # "machine_main"

    def __init__(self, service: MachineService, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = service
        self._unlocked = False
        self._confirmed_shown: set[str] = set()
        self._dirty: set[str] = set()  # keys with a genuine unsaved user edit
        # key -> (spin, apply_btn, status_label)
        self._rows: dict[str, tuple[QDoubleSpinBox, QPushButton, QLabel]] = {}
        self._build_ui()
        service.snapshotUpdated.connect(self._on_snapshot)
        service.parameterWriteConfirmed.connect(self._on_write_confirmed)
        service.parameterWriteFailed.connect(self._on_write_failed)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("AYARLAR / MÜHENDİSLİK")
        title.setFont(base_font(14, bold=True))
        back_btn = touch_button("◀ ANA EKRAN", object_name="navButton")
        back_btn.clicked.connect(lambda: self.navigateRequested.emit("machine_main"))
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(back_btn)
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
        grid.addWidget(self._header_label(""), 0, 3)
        grid.addWidget(self._header_label("Durum"), 0, 4)

        for row_index, spec in enumerate(PARAMETER_SPECS, start=1):
            name_label = QLabel(spec.label_tr)
            spin = QDoubleSpinBox()
            spin.setRange(spec.min_value, spec.max_value)
            spin.setDecimals(2)
            spin.setValue(self._service.get_parameter_value(spec.key))
            spin.setEnabled(False)
            # Only fires for a genuine user edit: our own live-sync/initial
            # setValue calls below are wrapped in blockSignals().
            spin.valueChanged.connect(lambda _v, key=spec.key: self._dirty.add(key))
            unit_label = QLabel(spec.unit)
            unit_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            apply_btn = touch_button("Uygula")
            apply_btn.setEnabled(False)
            status_label = QLabel("")

            apply_btn.clicked.connect(
                lambda _checked=False, key=spec.key, box=spin, label=status_label, spec_=spec: self._apply_parameter(
                    key, box, label, spec_
                )
            )

            grid.addWidget(name_label, row_index, 0)
            grid.addWidget(spin, row_index, 1)
            grid.addWidget(unit_label, row_index, 2)
            grid.addWidget(apply_btn, row_index, 3)
            grid.addWidget(status_label, row_index, 4)

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
        layout.addWidget(self._endpoint_save_btn)
        return card

    # -- data binding ---------------------------------------------------------

    def _on_snapshot(self, snap: MachineSnapshot) -> None:
        # Güvenlik (2026-09-16, kullanıcı isteği): makine xCycleActive iken
        # (otomatik çevrimde) Mühendislik erişimi açık kalamaz - çevrim
        # ortasında biri unlock alip devam ederse zorla kilitlenir.
        # `self._unlocked` HEMEN False yapılıyor ki bloklayan uyarı
        # penceresi sırasında gelecek bir sonraki tick tekrar tetiklemesin.
        if snap.cycle_active and self._unlocked:
            self._unlocked = False
            self._unlock_checkbox.blockSignals(True)
            self._unlock_checkbox.setChecked(False)
            self._unlock_checkbox.blockSignals(False)
            for key in self._rows:
                self._update_row_enabled(key)
            self._endpoint_edit.setEnabled(False)
            self._endpoint_save_btn.setEnabled(False)
            QMessageBox.warning(
                self,
                "Erişim Kapatıldı",
                "Makine otomatik çevrime girdi. Mühendislik erişimi güvenlik "
                "nedeniyle kapatıldı.",
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

    def _apply_parameter(self, key: str, spin: QDoubleSpinBox, status_label: QLabel, spec) -> None:
        value = spin.value()
        confirm = QMessageBox.question(
            self,
            "Parametre Değişikliği Onayı",
            f"{spec.label_tr} değeri {value:g} {spec.unit} olarak ayarlanacak.\nOnaylıyor musunuz?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
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
        status_label.setText("✓ UYGULANDI")
        status_label.setStyleSheet(f"color: {COLORS['success']};")

    def _on_write_failed(self, key: str) -> None:
        row = self._rows.get(key)
        if row is None:
            return
        _spin, _apply_btn, status_label = row
        self._dirty.discard(key)
        status_label.setText("HATA — PLC onaylamadı")
        status_label.setStyleSheet(f"color: {COLORS['danger']};")

    def _save_endpoint(self) -> None:
        endpoint = self._endpoint_edit.text().strip()
        self._service.update_endpoint(endpoint)
        QMessageBox.information(
            self,
            "Kaydedildi",
            "OPC UA endpoint kaydedildi. Değişikliğin etkili olması için uygulamayı yeniden başlatın.",
        )
