"""Sahte kamera (Vision simülatörü) sahaya giden pakette açılmaz (2026-09-26).

Yücel: "sahte kamera sim iptal etsin... makineye aktarımda disable ediyorum,
yoksa sürekli simülasyon CPU'yu darlar." Gerçek VisionCut aynı PLC alanlarını
yazıyor; simülatör de açılırsa iki yazar olur. Kural artık kodda: ayar
dosyası `vision_simulator_enabled: true` dese de derlenmiş exe'de kapalı.
"""

from __future__ import annotations

import sys

from services.machine_service import MachineService


def _config(tmp_path):
    cfg = tmp_path / "opcua.json"
    cfg.write_text('{"endpoint": "", "vision_simulator_enabled": true, "nodes": {}}',
                   encoding="utf-8")
    return cfg


def test_the_packaged_screen_never_offers_the_fake_camera(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert MachineService(config_path=_config(tmp_path)).vision_simulator_enabled is False


def test_from_source_it_still_follows_the_config(tmp_path, monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert MachineService(config_path=_config(tmp_path)).vision_simulator_enabled is True
