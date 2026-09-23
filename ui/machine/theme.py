"""VisionCut theme tokens (integration brief section 31) — reused verbatim
so the Makine Ekranı reads as part of the same product, not a foreign HMI.
If/when the real VisionCut theme module becomes available to us, this file
should be replaced by an import from it rather than kept as a duplicate."""

from __future__ import annotations

from PySide6.QtGui import QFont

COLORS = {
    "navy": "#1C2536",
    "page_bg": "#161D2B",
    "input_bg": "#243044",
    "accent_orange": "#F47C20",
    "brand_cyan": "#00DDFF",
    "danger": "#C53030",
    "warning": "#D97706",
    "success": "#2F855A",
    "text_primary": "#E8EAED",
    "text_secondary": "#9FADC4",
    "border": "#33415C",
    "text_muted": "#68758A",
}

FONT_FAMILY = "Segoe UI"

# Touch targets (brief section 3)
MIN_TOUCH_HEIGHT = 48
PRIMARY_ACTION_HEIGHT = 64


def base_font(point_size: int = 10, bold: bool = False) -> QFont:
    font = QFont(FONT_FAMILY, point_size)
    font.setBold(bold)
    return font


def tabular_font(point_size: int = 10, bold: bool = False) -> QFont:
    """Numeric readouts should not jitter horizontally as digits change.

    2026-09-23 (kullanıcı bulgusu, ekran görüntüsü): pencere büyütülüp
    küçültüldüğünde bu fontu kullanan sayıların (X/Y Pozisyonu, Actual
    Position vb.) bazen okunmaz/bozuk glifler gösterdiği görüldü -
    `QFont.setFeature(tnum, ...)` (PySide6 6.11.1, Windows) ile ilişkili bir
    yeniden-boyutlandırma/glif önbelleği sorunu olduğu değerlendirildi.
    Kaynakta bu tek özel OpenType özelliği tüm sayfalarda etkiliydi (Readout
    her yerde bunu kullanıyor) - kaldırıldı. Bedeli yalnız kozmetik (rakamlar
    değişirken hafif yatay titreşim olabilir); kazancı her zaman okunur
    metin - HMI için doğru takas."""
    font = base_font(point_size, bold)
    font.setStyleStrategy(QFont.StyleStrategy.PreferQuality)
    return font


STYLESHEET = f"""
QWidget {{
    background-color: {COLORS['page_bg']};
    color: {COLORS['text_primary']};
    font-family: '{FONT_FAMILY}';
}}

QLabel {{
    background: transparent;
}}

QCheckBox {{
    background: transparent;
}}

QFrame#card {{
    background-color: {COLORS['navy']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
}}

QFrame#statusBar {{
    background-color: {COLORS['navy']};
    border-bottom: 1px solid {COLORS['border']};
}}

QPushButton {{
    background-color: {COLORS['input_bg']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 14px;
}}

QPushButton:hover {{
    border-color: {COLORS['accent_orange']};
}}

QPushButton:pressed {{
    background-color: {COLORS['border']};
}}

QPushButton:disabled {{
    background-color: {COLORS['input_bg']};
    color: {COLORS['text_muted']};
    border-color: {COLORS['border']};
}}

QPushButton#startButton {{
    background-color: {COLORS['success']};
    color: {COLORS['text_primary']};
    font-weight: 600;
    font-size: 18px;
}}

QPushButton#stopButton {{
    background-color: {COLORS['danger']};
    color: {COLORS['text_primary']};
    font-weight: 600;
    font-size: 18px;
}}

QPushButton#resetButton {{
    background-color: {COLORS['warning']};
    color: {COLORS['text_primary']};
    font-weight: 600;
    font-size: 18px;
}}

QPushButton#applyButtonSmall {{
    padding: 2px 8px;
    font-size: 12px;
}}

QPushButton#navButton {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
}}

QPushButton#navButton:checked {{
    border-color: {COLORS['accent_orange']};
    color: {COLORS['accent_orange']};
}}

QPushButton#cameraButton {{
    border-color: {COLORS['brand_cyan']};
    color: {COLORS['brand_cyan']};
}}

QTableWidget {{
    background-color: {COLORS['navy']};
    gridline-color: {COLORS['border']};
    border: 1px solid {COLORS['border']};
}}

/* Kullanıcı bulgusu (2026-09-22): QTabWidget/QTabBar için hiç kural yoktu,
   bu yüzden OS'nin varsayılan (açık renkli) sekme çizimi kullanılıyordu -
   uygulamanın koyu temasındaki açık metin rengiyle üst üste binip
   okunmuyordu. Seçili/seçili-olmayan sekmeler artık her durumda okunur. */
QTabWidget::pane {{
    background-color: {COLORS['navy']};
    border: 1px solid {COLORS['border']};
    top: -1px;
}}

QTabBar::tab {{
    background-color: {COLORS['input_bg']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['navy']};
    color: {COLORS['accent_orange']};
    border-color: {COLORS['accent_orange']};
}}

QTabBar::tab:!selected:hover {{
    background-color: {COLORS['border']};
    color: {COLORS['text_primary']};
}}

QHeaderView::section {{
    background-color: {COLORS['input_bg']};
    color: {COLORS['text_secondary']};
    padding: 6px;
    border: none;
    border-bottom: 1px solid {COLORS['border']};
}}

QLineEdit, QDoubleSpinBox, QSpinBox {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px;
    color: {COLORS['text_primary']};
}}

QProgressBar {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    text-align: center;
    color: {COLORS['text_primary']};
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent_orange']};
    border-radius: 6px;
}}
"""
