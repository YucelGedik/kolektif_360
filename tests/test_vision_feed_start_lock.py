"""VisionCut canlı kare + Start kilidi (kanal mesajı 19, 22 §8).

Karar VisionCut'ın (durum.json: baslat_izni + neden); burada yalnız okunur.
Bayat ya da eksik dosya "izin yok" demektir. Kilit yalnız bu ekrandaki START
düğmesini tutar - paneldeki fiziksel START'ı kapsamaz.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from services.machine_service import MachineService  # noqa: E402
from services.vision_feed import VisionFeedReader, VisionFeedState  # noqa: E402
from ui.machine.machine_page import MachinePage  # noqa: E402


def _write(folder, allowed=True, reason="Kesim çizgisi çerçevede: +0.4 mm.", when=None):
    folder.mkdir(parents=True, exist_ok=True)
    stamp = (when or datetime.now(timezone.utc)).isoformat()
    # The exact shape VisionCut writes (brode_vision_console/services/hmi_feed.py).
    (folder / "durum.json").write_text(json.dumps({
        "cerceve_mm": 10.0, "kesimde": False, "baslat_izni": allowed,
        "neden": reason, "sapma_mm": 0.4, "zaman": stamp,
        "kare_yazildi": True, "surum": 1}, ensure_ascii=False), encoding="utf-8")


# -- reader -------------------------------------------------------------------

def test_no_file_means_no_start(tmp_path):
    state = VisionFeedReader(tmp_path / "yok").read()
    assert not state.fresh and not state.allowed
    assert "görüntüsü yok" in state.reason


def test_a_fresh_verdict_is_passed_through(tmp_path):
    _write(tmp_path, allowed=False, reason="Kesim çizgisi çerçevenin dışında: +12.0 mm")
    state = VisionFeedReader(tmp_path).read()
    assert state.fresh and not state.allowed
    assert "dışında" in state.reason


def test_a_stale_verdict_does_not_allow_start(tmp_path):
    _write(tmp_path, allowed=True)
    state = VisionFeedReader(tmp_path, clock=lambda: time.time() + 10.0).read()
    assert not state.allowed
    assert "yanıt vermiyor" in state.reason


# -- page ---------------------------------------------------------------------

class _Feed:
    def __init__(self, allowed: bool, reason: str = "Kesim çizgisi bulunamadı."):
        self.state = VisionFeedState(True, allowed, reason, False, None, 0.0)

    def read(self):
        return self.state


def _page(tmp_path, feed):
    cfg = tmp_path / "opcua.json"
    cfg.write_text(json.dumps({"endpoint": "opc.tcp://127.0.0.1:4840", "nodes": {}}),
                   encoding="utf-8")
    svc = MachineService(config_path=cfg)
    return MachinePage(svc, vision_feed=feed), svc


def _emit(page, svc, **overrides):
    snap = svc._snapshot
    values = {"stale": False, "start_permitted": True, "cycle_active": False}
    values.update(overrides)
    for key, value in values.items():
        setattr(snap, key, value)
    svc.snapshotUpdated.emit(snap)
    _app.processEvents()


def test_start_needs_the_camera_as_well_as_the_plc(tmp_path):
    feed = _Feed(allowed=True)
    page, svc = _page(tmp_path, feed)
    _emit(page, svc)
    assert page._start_btn.isEnabled()

    feed.state = VisionFeedState(True, False, "Kesim çizgisi bulunamadı.", False, None, 0.0)
    page._poll_vision_feed()
    assert not page._start_btn.isEnabled(), "kamera onayı yokken START açık kaldı"

    _emit(page, svc)
    assert any(r.startswith("[U12] Kamera: Kesim çizgisi bulunamadı")
               for r in page._live_warning_messages)


def test_the_camera_never_opens_what_the_plc_holds(tmp_path):
    page, svc = _page(tmp_path, _Feed(allowed=True))
    _emit(page, svc, start_permitted=False)
    assert not page._start_btn.isEnabled()


def test_no_camera_reason_during_the_cycle(tmp_path):
    page, svc = _page(tmp_path, _Feed(allowed=False))
    _emit(page, svc, cycle_active=True, start_permitted=False)
    assert not any(r.startswith("[U12]") for r in page._live_warning_messages)


def test_the_page_reads_a_real_file_pair(tmp_path):
    folder = tmp_path / "canli"
    _write(folder, allowed=True)
    page, svc = _page(tmp_path, VisionFeedReader(folder))
    _emit(page, svc)
    assert page._start_btn.isEnabled()
    assert "çerçevede" in page._vision_reason.text()


# -- VisionCut arızası burada da açıklanır (Murat, 2026-09-26) -----------------

_FAULT = {"kod": 400, "baslik": "Kesim sırasında kamera kesim çizgisini ölçemedi.",
          "cozum": "Kumaşı ve ışığı kontrol edin.",
          "ayrinti": "X=1902.3 mm için tamponlanmış hedef yok",
          "zaman": "2026-09-26T08:15:00+00:00"}


def test_a_vision_fault_is_explained_with_its_remedy(tmp_path):
    feed = _Feed(allowed=False, reason="VisionCut arızada")
    feed.state = VisionFeedState(True, False, "VisionCut arızada", False, None, 0.0,
                                 _FAULT, _FAULT)
    page, svc = _page(tmp_path, feed)
    page._poll_vision_feed()
    _emit(page, svc, cycle_active=True, start_permitted=False)

    label = page._vision_reason.text()
    assert "VisionCut arızası 400" in label and "Çözüm:" in label and "1902.3" in label

    rows = [(page._alarm_table.item(r, 1).text(), page._alarm_table.item(r, 2).text(),
             page._alarm_table.item(r, 3).text())
            for r in range(page._alarm_table.rowCount())]
    assert any(source == "VISION" and message.startswith("[V400]") for _sev, source, message in rows), rows


def test_the_last_fault_stays_readable_after_it_clears(tmp_path):
    feed = _Feed(allowed=True)
    feed.state = VisionFeedState(True, True, "Kesim çizgisi çerçevede: +0.4 mm.", False,
                                 None, 0.0, None, _FAULT)
    page, _svc = _page(tmp_path, feed)
    page._poll_vision_feed()
    assert "Son VisionCut arızası" in page._vision_reason.text()
    assert not page._live_error_rows, "temizlenmiş arıza hâlâ aktif hata satırı"


def test_state_20_says_start_is_awaited(tmp_path):
    from core.cycle_state import CycleState

    page, svc = _page(tmp_path, _Feed(allowed=True))
    _emit(page, svc, cycle_state=int(CycleState.WAIT_FOR_MATERIAL))
    assert any(m.startswith("[M10] Start bekleniyor") for m in page._live_message_texts)


def test_the_screen_opens_full_screen():
    import inspect

    import app.main as main_module

    assert "window.showMaximized()" in inspect.getsource(main_module)


# -- OK / OK DEĞİL ışığı (Yücel, 2026-09-26) ------------------------------------

def test_the_light_reads_at_a_glance():
    from ui.machine.machine_page import vision_light

    ok = VisionFeedState(True, True, "çerçevede", False, None, 0.0)
    out = VisionFeedState(True, False, "dışında", False, None, 0.0)
    cut = VisionFeedState(True, False, "Kesim sürüyor.", True, None, 0.0)
    fault = VisionFeedState(True, False, "arızada", False, None, 0.0, _FAULT, _FAULT)
    gone = VisionFeedState(False, False, "yok", False, None, 0.0)

    assert vision_light(ok)[:2] == ("✓", "HAZIR")
    assert vision_light(out)[:2] == ("✗", "HAZIR DEĞİL")
    assert vision_light(cut)[:2] == ("●", "KESİMDE")
    assert vision_light(fault)[:2] == ("✗", "ARIZA")
    assert vision_light(gone)[:2] == ("✗", "VISIONCUT YOK")


def test_the_light_is_on_the_page(tmp_path):
    page, _svc = _page(tmp_path, _Feed(allowed=True))
    page._poll_vision_feed()
    assert page._vision_light.text() == "✓\nHAZIR"
