"""Makine Ekranı — application entry point.

VisionCut is a SEPARATE PROGRAM in a separate process (KARARLAR.md #1), not a
page inside this one. The placeholder "Kamera Ekranı" page that used to stand
in for it is gone: in a two-process panel there is nothing for it to stand in
for, and a fake camera screen beside a real one is the kind of placeholder
that lights a green light nobody earned.

"KAMERA EKRANI" therefore hands the panel over instead of switching pages —
see `app/companion.py` for why it launches as well as raises, and why this
window minimises itself on the way out.
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from app.companion import SingleInstance, raise_existing_instance, show_vision_screen

from persistence.db import init_engine
from services.machine_service import MachineService
from ui.machine.alarm_page import AlarmPage
from ui.machine.machine_page import MachinePage
from ui.machine.manual_page import ManualPage
from ui.machine.settings_page import SettingsPage
from ui.machine.theme import STYLESHEET
from ui.machine.widgets import MachineStatusBar, SectionTabs


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

        self._machine_page = MachinePage(service)
        self._manual_page = ManualPage(service)
        self._settings_page = SettingsPage(service)
        self._alarm_page = AlarmPage(service)

        # "camera" is deliberately absent: it is an action, not a page.
        self._pages = {
            "machine_main": self._machine_page,
            "manual": self._manual_page,
            "settings": self._settings_page,
            "alarms": self._alarm_page,
        }
        for page in self._pages.values():
            self._stack.addWidget(page)

        # Opens on the machine's own main page. It used to open on the
        # placeholder camera page, which in a two-process panel showed the
        # operator a fake version of a program running next door.
        self._navigate("machine_main")

    def _navigate(self, key: str) -> None:
        if key == "camera":
            self._hand_over_to_vision()
            return
        self._stack.setCurrentWidget(self._pages[key])
        self._nav.set_active(key)

    def _hand_over_to_vision(self) -> str:
        """Put VisionCut in front of the operator and step aside.

        ⚠️ The order matters. Windows will usually refuse SetForegroundWindow
        to a process that does not own the foreground, so raising VisionCut is
        only a request; minimising OURSELVES is what actually reveals it. We
        minimise only when there is something to reveal -- if VisionCut is not
        installed, stepping aside would leave the operator looking at the
        desktop with no way back on a kiosk with no taskbar.
        """
        outcome = show_vision_screen(self._service.config.vision_exe)
        if outcome in ("raised", "launched"):
            self.showMinimized()
        return outcome

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

    # One copy only: a second would open a second OPC UA session and write
    # the same tags. The second launch raises the first window and exits.
    instance = SingleInstance()
    if not instance.is_first:
        logging.warning("Makine Ekranı zaten çalışıyor; var olan pencere öne alındı.")
        raise_existing_instance()
        return 0

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    service = MachineService()

    window = MainWindow(service)
    window.show()

    # Started only after the pages exist and have subscribed to the
    # service's signals, so the very first connectionStateChanged/
    # snapshotUpdated emissions (e.g. entering Demo mode) aren't missed.
    service.start()

    try:
        return app.exec()
    finally:
        instance.release()


if __name__ == "__main__":
    sys.exit(main())
