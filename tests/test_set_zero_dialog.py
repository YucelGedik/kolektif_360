"""PLC-HMI-20260923-20 (C8, "Sıfır Referansı Belirle", sade sürüm): widget-
seviyesi testler - `SetZeroReferenceDialog`'un kendisi (hold/cancel/kapatma
engeli) ve `SettingsPage`'deki şifre kapısı. Gerçek bir PLC'ye bağlanılmaz;
`.exec()` (application-modal, bloklayan) hiçbir testte çağrılmaz - dialog
doğrudan `.show()` ile (ya da hiç gösterilmeden) test edilir."""

from __future__ import annotations

import contextlib
import json
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

import persistence.db as db_module
from core.models import ConnectionState
from services.machine_service import MachineService
from ui.machine.set_zero_dialog import SetZeroReferenceDialog
from ui.machine.settings_page import VISION_SIM_PASSWORD, SettingsPage

MANUAL = 10  # CycleState.MANUAL

_NODES = {
    "cmd_set_zero_request": "ns=4;s=|var|MAT LC-C07.Application.GVL.xSetZeroRequest",
    "x_home_done": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_X.Done",
    "x_home_busy": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_X.Busy",
    "x_home_error": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_X.Error",
    "x_home_error_id": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_X.ErrorID",
    "x_home_aborted": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_X.CommandAborted",
    "y_home_done": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_Y.Done",
    "y_home_busy": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_Y.Busy",
    "y_home_error": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_Y.Error",
    "y_home_error_id": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_Y.ErrorID",
    "y_home_aborted": "ns=4;s=|var|MAT LC-C07.Application.Motion_Control.MC_Home_Y.CommandAborted",
}


@contextlib.contextmanager
def _isolated_engine(tmp_path):
    db_module.init_engine(tmp_path / "test_set_zero_dialog.db")
    try:
        yield
    finally:
        db_module.init_engine()


def _ready_service(tmp_path) -> MachineService:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(
        json.dumps({"endpoint": "opc.tcp://192.168.0.2:4840", "nodes": _NODES}), encoding="utf-8"
    )
    svc = MachineService(config_path=cfg)
    svc._worker = MagicMock()
    svc.snapshot.connection_state = ConnectionState.CONNECTED
    svc.snapshot.stale = False
    svc.snapshot.manual_mode = True
    svc.snapshot.cycle_state = MANUAL
    svc.snapshot.emergency_ok = True
    svc.snapshot.x_servo_ready = True
    svc.snapshot.y_servo_ready = True
    svc.snapshot.blade_down = False
    svc.snapshot.clamp_down = False
    return svc


# -- SettingsPage şifre kapısı (C8-S02) ---------------------------------


def _settings_page(tmp_path) -> SettingsPage:
    cfg = tmp_path / "opcua.json"
    cfg.write_text('{"endpoint": "", "nodes": {}}', encoding="utf-8")
    svc = MachineService(config_path=cfg)
    page = SettingsPage(svc)
    page._unlock_checkbox.setChecked(True)
    return page


def test_wrong_password_does_not_open_dialog_no_command_created(tmp_path):
    page = _settings_page(tmp_path)
    with patch(
        "ui.machine.settings_page.QInputDialog.getText", return_value=("11111", True)
    ), patch("ui.machine.settings_page.QMessageBox.warning") as warn, patch(
        "ui.machine.settings_page.SetZeroReferenceDialog"
    ) as dialog_cls:
        page._open_set_zero_dialog()

    dialog_cls.assert_not_called()
    warn.assert_called_once()


def test_cancelling_password_prompt_does_not_open_dialog(tmp_path):
    page = _settings_page(tmp_path)
    with patch(
        "ui.machine.settings_page.QInputDialog.getText", return_value=("", False)
    ), patch("ui.machine.settings_page.SetZeroReferenceDialog") as dialog_cls:
        page._open_set_zero_dialog()

    dialog_cls.assert_not_called()


def test_correct_password_opens_the_modal_dialog(tmp_path):
    page = _settings_page(tmp_path)
    with patch(
        "ui.machine.settings_page.QInputDialog.getText",
        return_value=(VISION_SIM_PASSWORD, True),
    ), patch("ui.machine.settings_page.SetZeroReferenceDialog") as dialog_cls:
        page._open_set_zero_dialog()

    dialog_cls.assert_called_once()
    dialog_cls.return_value.exec.assert_called_once()


def test_reopening_asks_for_password_again_no_caching(tmp_path):
    page = _settings_page(tmp_path)
    with patch(
        "ui.machine.settings_page.QInputDialog.getText",
        return_value=(VISION_SIM_PASSWORD, True),
    ) as prompt, patch("ui.machine.settings_page.SetZeroReferenceDialog"):
        page._open_set_zero_dialog()
        page._open_set_zero_dialog()

    assert prompt.call_count == 2


# -- Diyalog davranışı (C8-S02/S04) --------------------------------------


def test_button_enabled_when_conditions_met(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _ready_service(tmp_path)
        dialog = SetZeroReferenceDialog(svc)

        assert dialog._button.isEnabled() is True


def test_button_disabled_when_conditions_not_met(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _ready_service(tmp_path)
        svc.snapshot.manual_mode = False
        dialog = SetZeroReferenceDialog(svc)
        svc.snapshotUpdated.emit(svc.snapshot)

        assert dialog._button.isEnabled() is False


def test_missing_tags_shows_honest_reason_not_generic_conditions_text(tmp_path):
    """PLC-HMI-20260923-22/23 (kullanıcı bulgusu + PLC düzeltmesi, gerçek
    PLC testi): tag'ler config'te yokken eskiden genel "koşullar
    sağlanmıyor: manuel mod/servo/mekanizma" metni gösteriliyordu - operatör
    kendi kurulumunu sorguluyordu. Sonra "PLC henüz online doğrulamadı"
    dendi - bu da yanlıştı (salt-okunur browse `xSetZeroRequest`'in canlı
    olduğunu doğruladı, yalnız 10 MC_Home RO alanı yayınlanmamış). Doğru,
    nötr metin: "HMI bağlantı ayarında ... eksik" + hangi anahtarlar."""
    with _isolated_engine(tmp_path):
        # Koşulların hepsi sağlanıyor (manuel/servo/emergency) - ama tag'ler
        # config'te hiç yok (`nodes: {}`), gerçek PLC'deki durumu taklit eder.
        cfg = tmp_path / "opcua_no_tags.json"
        cfg.write_text(json.dumps({"endpoint": "opc.tcp://192.168.0.2:4840", "nodes": {}}), encoding="utf-8")
        svc = MachineService(config_path=cfg)
        svc._worker = MagicMock()
        svc.snapshot.connection_state = ConnectionState.CONNECTED
        svc.snapshot.stale = False
        svc.snapshot.manual_mode = True
        svc.snapshot.cycle_state = MANUAL
        svc.snapshot.emergency_ok = True
        svc.snapshot.x_servo_ready = True
        svc.snapshot.y_servo_ready = True

        dialog = SetZeroReferenceDialog(svc)

        assert dialog._button.isEnabled() is False
        text = dialog._condition_label.text()
        assert "HMI bağlantı ayarında sıfırlama alanları eksik" in text
        assert "cmd_set_zero_request" in text  # eksik anahtarlar teşhiste görünür
        assert "manuel" not in text.lower()
        assert "PLC" not in text or "doğrulamadı" not in text  # "PLC henüz doğrulamadı" iddiası YOK


def test_early_release_cancels_hold_without_sending_request(tmp_path):
    """C8-S02: "3 saniye erken bırakma ... talep oluşmaz." """
    with _isolated_engine(tmp_path):
        svc = _ready_service(tmp_path)
        dialog = SetZeroReferenceDialog(svc)

        dialog._on_held(True)
        assert dialog._holding is True

        dialog._on_held(False)

        assert dialog._holding is False
        svc._worker.request_write.assert_not_called()
        assert svc.set_zero_status() == "idle"


def test_hold_complete_sends_the_request(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _ready_service(tmp_path)
        dialog = SetZeroReferenceDialog(svc)

        dialog._on_held(True)
        dialog._on_hold_complete()

        svc._worker.request_write.assert_called_once_with("cmd_set_zero_request", True)
        assert svc.set_zero_status() == "sent"


def test_conditions_lost_mid_hold_cancels_it(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _ready_service(tmp_path)
        dialog = SetZeroReferenceDialog(svc)
        dialog._on_held(True)
        assert dialog._holding is True

        svc.snapshot.emergency_ok = False  # EMG tekrar basıldı
        svc.snapshotUpdated.emit(svc.snapshot)

        assert dialog._holding is False
        svc._worker.request_write.assert_not_called()


def test_hold_complete_when_conditions_slipped_shows_warning_sends_nothing(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _ready_service(tmp_path)
        dialog = SetZeroReferenceDialog(svc)
        dialog._on_held(True)
        svc.snapshot.manual_mode = False  # basılı tutarken koşul bozuldu

        with patch("ui.machine.set_zero_dialog.QMessageBox.warning") as warn:
            dialog._on_hold_complete()

        warn.assert_called_once()
        svc._worker.request_write.assert_not_called()


def test_dialog_cannot_be_closed_while_sent_or_busy(tmp_path):
    """Görev notu: "İşlem sırasında ... modal pencere normal olarak
    kapatılamaz." """
    with _isolated_engine(tmp_path):
        svc = _ready_service(tmp_path)
        dialog = SetZeroReferenceDialog(svc)
        dialog.show()

        dialog._on_held(True)
        dialog._on_hold_complete()
        assert svc.set_zero_status() == "sent"

        dialog.close()
        assert dialog.isVisible() is True  # reddedildi

        dialog.reject()
        assert dialog.isVisible() is True  # Esc de reddedildi


def test_dialog_closes_normally_once_result_lands(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _ready_service(tmp_path)
        dialog = SetZeroReferenceDialog(svc)
        dialog.show()
        dialog._on_held(True)
        dialog._on_hold_complete()

        svc._on_raw_snapshot({"x_home_busy": True, "y_home_busy": True})
        svc._on_raw_snapshot(
            {"x_home_busy": False, "y_home_busy": False, "x_home_done": True, "y_home_done": True}
        )
        svc.snapshotUpdated.emit(svc.snapshot)
        assert svc.set_zero_status() == "done"

        dialog.close()

        assert dialog.isVisible() is False


def test_success_result_shown_in_result_label(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _ready_service(tmp_path)
        dialog = SetZeroReferenceDialog(svc)
        dialog._on_held(True)
        dialog._on_hold_complete()
        svc._on_raw_snapshot({"x_home_busy": True, "y_home_busy": True})
        svc._on_raw_snapshot(
            {"x_home_busy": False, "y_home_busy": False, "x_home_done": True, "y_home_done": True}
        )
        svc.snapshotUpdated.emit(svc.snapshot)

        assert dialog._result_label.text() == "X ve Y sıfır referansı belirlendi."


def test_error_result_shown_with_error_id(tmp_path):
    with _isolated_engine(tmp_path):
        svc = _ready_service(tmp_path)
        dialog = SetZeroReferenceDialog(svc)
        dialog._on_held(True)
        dialog._on_hold_complete()
        svc._on_raw_snapshot({"x_home_busy": True, "y_home_busy": True})
        svc._on_raw_snapshot(
            {"x_home_busy": False, "y_home_busy": False, "x_home_error": True, "x_home_error_id": 7}
        )
        svc.snapshotUpdated.emit(svc.snapshot)

        assert "HataID: 7" in dialog._result_label.text()
        assert "Sıfırlama tamamlanamadı" in dialog._result_label.text()
