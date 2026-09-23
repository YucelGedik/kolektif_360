"""Standalone development/demo host shell.

This is NOT the real VisionCut application — VisionCut belongs to another
company and its source is not available to us (see INTEGRATION.md). This
shell exists only so the Makine Ekranı can be built, run and demoed without
it: a placeholder "Kamera Ekranı" page stands in for VisionCut's real camera
UI, with a single "Makine Ekranı" button, matching the navigation contract
described in the integration brief (section 5 & 29).
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from persistence.db import init_engine
from services.machine_service import MachineService
from ui.machine.alarm_page import AlarmPage
from ui.machine.machine_page import MachinePage
from ui.machine.manual_page import ManualPage
from ui.machine.settings_page import SettingsPage
from ui.machine.theme import STYLESHEET
from ui.machine.widgets import MachineStatusBar, SectionTabs


class CameraPlaceholderPage(QWidget):
    """Stand-in for VisionCut's real camera screen (not ours to build)."""

    navigateRequested = Signal(str)  # "machine_main"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(layout.alignment())
        title = QLabel("VisionCut — Kamera Ekranı (yer tutucu)")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        subtitle = QLabel(
            "Gerçek VisionCut uygulaması bu makinede mevcut değil.\n"
            "Bu ekran yalnızca geliştirme/test amaçlı bir yer tutucudur."
        )
        subtitle.setStyleSheet("color: #9FADC4;")
        button = QPushButton("Makine Ekranı")
        button.setObjectName("cameraButton")
        button.setMinimumHeight(64)
        button.clicked.connect(lambda: self.navigateRequested.emit("machine_main"))

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(button)
        layout.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self, service: MachineService):
        super().__init__()
        # VisionCut mesaj 08.2: kendi programları bizimkini pencere
        # başlığında "Makine Ekran" alt dizesiyle buluyor - bu ifade
        # KORUNMALI. "(dev shell)" kaldırıldı (görev notu, 2026-09-23).
        self.setWindowTitle("Bufera — VisionCut / Makine Ekranı")
        self.resize(1024, 768)

        self._service = service

        # Kullanıcı isteği (2026-09-23): üst özet çubuğu ve alt gezinme satırı
        # artık her sayfada aynı, TEK sabit örnek - sayfa değiştikçe yeniden
        # kurulmaz/kaybolmaz. `MachinePage` kendi başına bir statü çubuğu/nav
        # inşa etmiyor artık (bkz. machine_page.py).
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self._status_bar = MachineStatusBar(service)
        central_layout.addWidget(self._status_bar)

        self._stack = QStackedWidget()
        central_layout.addWidget(self._stack, stretch=1)

        # "ANA SAYFA" en başa eklendi (kullanıcı isteği): her sayfadan tek
        # tıkla ana ekrana dönülür, sayfa başlıklarındaki ayrı "◀ ANA EKRAN"
        # butonlarına gerek kalmadı (kaldırıldılar).
        self._nav = SectionTabs(
            [
                ("machine_main", "ANA SAYFA"),
                ("manual", "MANUEL"),
                ("settings", "AYARLAR"),
                ("alarms", "ALARMLAR"),
                ("camera", "KAMERA EKRANI"),
            ]
        )
        self._nav.button("camera").setObjectName("cameraButton")
        self._nav.tabClicked.connect(self._navigate)
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(12, 8, 12, 12)
        nav_layout.addWidget(self._nav)
        central_layout.addWidget(nav_container)

        self.setCentralWidget(central)

        self._camera_page = CameraPlaceholderPage()
        self._machine_page = MachinePage(service)
        self._manual_page = ManualPage(service)
        self._settings_page = SettingsPage(service)
        self._alarm_page = AlarmPage(service)

        self._pages = {
            "camera": self._camera_page,
            "machine_main": self._machine_page,
            "manual": self._manual_page,
            "settings": self._settings_page,
            "alarms": self._alarm_page,
        }
        for page in self._pages.values():
            self._stack.addWidget(page)

        self._camera_page.navigateRequested.connect(self._navigate)

        self._navigate("camera")

    def _navigate(self, key: str) -> None:
        self._stack.setCurrentWidget(self._pages[key])
        self._nav.set_active(key)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._service.shutdown()
        super().closeEvent(event)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_engine()

    # Kullanıcı bulgusu (2026-09-23): pencere laptop panelinden (kesirli DPI
    # ölçeği - örn. %150) ikinci bir monitöre (tam sayı ölçek, örn. %100)
    # taşınınca/tam ekran yapılınca metin (özellikle Readout sayıları)
    # bozuk glifler gösteriyordu, ikinci ekrana geçince düzeliyordu. Qt'nin
    # VARSAYILAN DPI ölçek-faktörü yuvarlama politikası (Round) kesirli
    # ölçeklerde layout/çizim geçişleri arasında tutarsız yuvarlamaya, bu da
    # ekranlar arası geçişte glif önbelleğinin bozulmasına yol açabiliyor -
    # QApplication oluşturulmadan ÖNCE PassThrough politikasına geçilmesi
    # (gerçek ölçek faktörünü hiç yuvarlamadan kullanmak) bu sınıf sorun için
    # Qt topluluğunda standart düzeltmedir.
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    service = MachineService()

    window = MainWindow(service)
    window.show()

    # Started only after the pages exist and have subscribed to the
    # service's signals, so the very first connectionStateChanged/
    # snapshotUpdated emissions (e.g. entering Demo mode) aren't missed.
    service.start()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
