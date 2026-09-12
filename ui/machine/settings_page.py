"""Screen C — Ayarlar / Mühendislik ekranı (integration brief section 8-C,
13, 24). Kept separate from the operator screen; parameter edits require an
explicit "Mühendislik Erişimi" unlock plus a confirmation dialog per edit,
since these are mechanical/motion limits (brief section 8: "Kritik mekanik
parametrelerin yanlışlıkla değiştirilmemesi için confirmation ...")."""

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
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.parameters import PARAMETER_SPECS
from services.machine_service import MachineService
from ui.machine.theme import COLORS, base_font
from ui.machine.widgets import touch_button


class SettingsPage(QWidget):
    navigateRequested = Signal(str)  # "machine_main"

    def __init__(self, service: MachineService, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = service
        self._rows: dict[str, tuple[QDoubleSpinBox, QLabel]] = {}
        self._build_ui()

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

        self._apply_buttons: list[tuple[QDoubleSpinBox, QWidget]] = []
        for row_index, spec in enumerate(PARAMETER_SPECS, start=1):
            name_label = QLabel(spec.label_tr)
            spin = QDoubleSpinBox()
            spin.setRange(spec.min_value, spec.max_value)
            spin.setDecimals(2)
            spin.setValue(self._service.get_parameter_value(spec.key))
            spin.setEnabled(False)
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

            self._rows[spec.key] = (spin, status_label)
            self._apply_buttons.append((spin, apply_btn))

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

    # -- interactions ---------------------------------------------------------

    def _on_unlock_toggled(self, checked: bool) -> None:
        for spin, apply_btn in self._apply_buttons:
            spin.setEnabled(checked)
            apply_btn.setEnabled(checked)
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
        # Best-effort verification: re-read what the service now reports.
        # Against a real PLC this reflects the last write until the next
        # OPC UA read tick confirms it round-tripped through the tag.
        confirmed = abs(self._service.get_parameter_value(key) - value) < 1e-6
        status_label.setText("✓ UYGULANDI" if confirmed else "?")
        status_label.setStyleSheet(f"color: {COLORS['success'] if confirmed else COLORS['warning']};")

    def _save_endpoint(self) -> None:
        endpoint = self._endpoint_edit.text().strip()
        self._service.update_endpoint(endpoint)
        QMessageBox.information(
            self,
            "Kaydedildi",
            "OPC UA endpoint kaydedildi. Değişikliğin etkili olması için uygulamayı yeniden başlatın.",
        )
