"""Değişmeyen şey yeniden çizilmez (2026-09-26 ölçümü).

Makine Ekranı Demo'da tek çekirdeğin %78'ini kullanıyordu: durum kartları her
PLC snapshot'ında (10 Hz) aynı rengi yeniden yazıyor (15 s'de 5655
setStyleSheet), alarm tablosu her snapshot'ta veritabanından sıfırdan
kuruluyordu. IPC'de bu işlemciyi kesim sırasında VisionCut paylaşıyor.
"""

from __future__ import annotations

import json

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from services.machine_service import MachineService  # noqa: E402
from ui.machine.machine_page import MachinePage  # noqa: E402
from ui.machine.widgets import ProcessStatusCard  # noqa: E402


def test_an_unchanged_status_is_not_restyled():
    card = ProcessStatusCard("Bıçak")
    calls = []
    original = card._label.setStyleSheet
    card._label.setStyleSheet = lambda sheet: (calls.append(sheet), original(sheet))

    for _ in range(10):
        card.set_status("YUKARI", "ok")
    card.set_status("AŞAĞI", "warn")

    assert len(calls) == 2, f"{len(calls)} kez yeniden stillendi"


class _Feed:
    def read(self):
        from services.vision_feed import VisionFeedState
        return VisionFeedState(True, True, "test", False, None, 0.0)


def test_the_alarm_table_is_not_rebuilt_on_an_unchanged_snapshot(tmp_path):
    cfg = tmp_path / "opcua.json"
    cfg.write_text(json.dumps({"endpoint": "opc.tcp://127.0.0.1:4840", "nodes": {}}),
                   encoding="utf-8")
    svc = MachineService(config_path=cfg)
    page = MachinePage(svc, vision_feed=_Feed())
    rebuilt = []
    original = page._refresh_alarm_table
    page._refresh_alarm_table = lambda: (rebuilt.append(1), original())

    snap = svc._snapshot
    snap.stale, snap.start_permitted, snap.cycle_active = False, True, False
    for _ in range(10):
        svc.snapshotUpdated.emit(snap)
        _app.processEvents()

    assert len(rebuilt) <= 1, f"aynı snapshot'ta tablo {len(rebuilt)} kez kuruldu"
