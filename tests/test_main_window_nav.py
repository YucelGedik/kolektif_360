"""Kullanıcı isteği (2026-09-23): üst özet çubuğu ve alt gezinme satırı artık
her sayfada aynı, TEK sabit örnek - `MainWindow` tarafından `QStackedWidget`in
dışında tutulur, sayfa değişince yeniden kurulmaz. "ANA SAYFA" en başa eklendi;
sayfaların kendi "◀ ANA EKRAN" butonları kaldırıldı (artık gereksiz)."""

from __future__ import annotations

import json

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from app.main import MainWindow
from services.machine_service import MachineService


def _window(tmp_path) -> MainWindow:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(json.dumps({"endpoint": "", "nodes": {}}), encoding="utf-8")
    svc = MachineService(config_path=cfg)
    return MainWindow(svc)


def test_status_bar_and_nav_are_single_shared_instances(tmp_path):
    win = _window(tmp_path)
    status_bar_id = id(win._status_bar)
    nav_id = id(win._nav)

    for key in ("machine_main", "manual", "settings", "alarms", "camera"):
        win._navigate(key)
        assert id(win._status_bar) == status_bar_id
        assert id(win._nav) == nav_id


def test_home_button_is_first_and_switches_to_machine_main(tmp_path):
    win = _window(tmp_path)
    keys = list(win._nav._buttons.keys())
    assert keys[0] == "machine_main"
    assert win._nav.button("machine_main").text() == "ANA SAYFA"

    win._navigate("settings")
    win._nav.button("machine_main").click()
    assert win._stack.currentWidget() is win._machine_page


def test_navigating_highlights_only_the_active_tab(tmp_path):
    win = _window(tmp_path)
    win._navigate("settings")
    for key in ("machine_main", "manual", "settings", "alarms", "camera"):
        assert win._nav.button(key).isChecked() == (key == "settings")

    win._navigate("alarms")
    for key in ("machine_main", "manual", "settings", "alarms", "camera"):
        assert win._nav.button(key).isChecked() == (key == "alarms")


def test_pages_no_longer_carry_their_own_back_navigation_signal(tmp_path):
    """"◀ ANA EKRAN" butonları kaldırıldı - dönüş artık yalnız paylaşılan
    alt navigasyondan ("ANA SAYFA")."""
    win = _window(tmp_path)
    for page in (win._manual_page, win._settings_page, win._alarm_page, win._machine_page):
        assert not hasattr(page, "navigateRequested")
