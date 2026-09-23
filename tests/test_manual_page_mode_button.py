"""Kullanıcı isteği (2026-09-23): ikinci bir "OTO MODU ETKİNLEŞTİR" butonu
eklemek yerine, tek mod butonu basılınca GEÇİLECEK moda göre etiketlenir -
Manuel'deyken "OTO MODU ETKİNLEŞTİR" (basınca Auto'ya döner), Auto'dayken
"MANUEL MODU ETKİNLEŞTİR" (basınca Manuel'e geçer). Ana ekranın "oto moda
geçin" uyarısına karşılık gelen buton görünür olsun, ayrı bir buton
olmadığı için kafa karışıklığı olmasın."""

from __future__ import annotations

import json

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from services.machine_service import MachineService
from ui.machine.manual_page import ManualPage


def _page(tmp_path) -> tuple[ManualPage, MachineService]:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(json.dumps({"endpoint": "", "nodes": {}}), encoding="utf-8")
    svc = MachineService(config_path=cfg)
    page = ManualPage(svc)
    return page, svc


def _emit(svc: MachineService, **overrides) -> None:
    snap = svc._snapshot
    for key, value in overrides.items():
        setattr(snap, key, value)
    svc.snapshotUpdated.emit(snap)
    _app.processEvents()


def test_button_shows_oto_modu_etkinlestir_while_in_manual(tmp_path):
    page, svc = _page(tmp_path)

    _emit(svc, manual_mode=True)

    assert page._manual_mode_btn.text() == "OTO MODU ETKİNLEŞTİR"
    assert page._manual_mode_btn.isChecked() is True


def test_button_shows_manuel_modu_etkinlestir_while_in_auto(tmp_path):
    page, svc = _page(tmp_path)

    _emit(svc, manual_mode=False)

    assert page._manual_mode_btn.text() == "MANUEL MODU ETKİNLEŞTİR"
    assert page._manual_mode_btn.isChecked() is False


def test_button_label_flips_when_mode_toggles(tmp_path):
    page, svc = _page(tmp_path)

    _emit(svc, manual_mode=False)
    assert page._manual_mode_btn.text() == "MANUEL MODU ETKİNLEŞTİR"

    _emit(svc, manual_mode=True)
    assert page._manual_mode_btn.text() == "OTO MODU ETKİNLEŞTİR"

    _emit(svc, manual_mode=False)
    assert page._manual_mode_btn.text() == "MANUEL MODU ETKİNLEŞTİR"


def test_clicking_the_button_still_writes_the_intended_next_mode(tmp_path):
    """Buton metni değişse de bağlı davranış aynı kalır: `clicked(bool)`
    Qt'nin verdiği YENİ checked durumunu taşır, `set_manual_mode`'a doğru
    hedef mod olarak gider. `stale=False` gerekli - demo modda `.start()`
    çağrılmadan `_mode_change_allowed()` bayat veriyle her zaman reddeder."""
    page, svc = _page(tmp_path)
    _emit(svc, manual_mode=False, stale=False)
    assert page._manual_mode_btn.text() == "MANUEL MODU ETKİNLEŞTİR"

    page._manual_mode_btn.click()  # Auto -> Manuel

    assert svc.demo_mode is True
    assert svc._demo.manual_mode is True
