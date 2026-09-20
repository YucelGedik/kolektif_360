"""Kullanıcı talebi (2026-09-18): Vision simülatörü butonuna ek bir şifre
kapısı (90327, 5 hane) - Mühendislik Erişimi zaten açık olsa bile HER
açılışta yeniden sorulur, hiçbir yerde önbelleğe alınmaz. Gerçek bir PLC'ye
bağlanılmaz - demo mod kullanılır."""

from __future__ import annotations

from unittest.mock import patch

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from services.machine_service import MachineService
from ui.machine.settings_page import VISION_SIM_PASSWORD, SettingsPage


def _page(tmp_path) -> SettingsPage:
    cfg = tmp_path / "opcua.json"
    cfg.write_text('{"endpoint": "", "vision_simulator_enabled": true, "nodes": {}}', encoding="utf-8")
    svc = MachineService(config_path=cfg)
    page = SettingsPage(svc)
    page._unlock_checkbox.setChecked(True)
    return page


def test_wrong_password_refuses_to_open(tmp_path):
    page = _page(tmp_path)

    with patch("ui.machine.settings_page.QInputDialog.getText", return_value=("11111", True)), patch(
        "ui.machine.settings_page.QMessageBox.warning"
    ) as warn:
        page._open_vision_simulator()

    assert page._vision_dialog is None
    warn.assert_called_once()


def test_cancelling_the_password_prompt_refuses_to_open(tmp_path):
    page = _page(tmp_path)

    with patch("ui.machine.settings_page.QInputDialog.getText", return_value=("", False)):
        page._open_vision_simulator()

    assert page._vision_dialog is None


def test_correct_password_opens_the_dialog(tmp_path):
    page = _page(tmp_path)

    with patch(
        "ui.machine.settings_page.QInputDialog.getText", return_value=(VISION_SIM_PASSWORD, True)
    ):
        page._open_vision_simulator()

    assert page._vision_dialog is not None
    assert page._vision_dialog.isVisible()


def test_reopening_after_close_asks_for_password_again(tmp_path):
    page = _page(tmp_path)

    with patch(
        "ui.machine.settings_page.QInputDialog.getText", return_value=(VISION_SIM_PASSWORD, True)
    ) as prompt:
        page._open_vision_simulator()
        assert prompt.call_count == 1
        page._vision_dialog.close()

        # Kapatıp aynı oturumda tekrar açmayı dener - önbellek yok, tekrar sorulmalı.
        page._open_vision_simulator()
        assert prompt.call_count == 2


def test_reopening_after_close_with_wrong_password_stays_closed(tmp_path):
    page = _page(tmp_path)

    with patch(
        "ui.machine.settings_page.QInputDialog.getText", return_value=(VISION_SIM_PASSWORD, True)
    ):
        page._open_vision_simulator()
    dialog = page._vision_dialog
    dialog.close()

    with patch("ui.machine.settings_page.QInputDialog.getText", return_value=("00000", True)), patch(
        "ui.machine.settings_page.QMessageBox.warning"
    ):
        page._open_vision_simulator()

    assert dialog.isVisible() is False
