"""VisionCut mesaj 08 (madde a/b, `INTEGRATION.md`): iki gerçek paketleme
hatası - (a) config dosyası yoksa/okunamıyorsa uygulama çökmemeli, Demo
moda düşmeli; (b) config/data yolları paketli (frozen, PyInstaller) bir
`.exe`de proje kaynak ağacına değil, `.exe`nin bulunduğu klasöre göre
çözülmeli (geçici/salt-okunur açılım dizini değil)."""

from __future__ import annotations

import json
import sys

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

import core.app_paths as app_paths
from services.machine_service import MachineService


def test_missing_config_file_falls_back_to_demo_mode_instead_of_crashing(tmp_path):
    missing = tmp_path / "does_not_exist.json"

    svc = MachineService(config_path=missing)  # raises nothing

    assert svc.demo_mode is True
    assert svc._config.endpoint == ""


def test_invalid_json_config_falls_back_to_demo_mode_instead_of_crashing(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")

    svc = MachineService(config_path=bad)  # raises nothing

    assert svc.demo_mode is True


def test_app_base_dir_is_project_root_when_not_frozen(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    base = app_paths.app_base_dir()

    assert (base / "app" / "main.py").exists()


def test_app_base_dir_is_executable_folder_when_frozen(monkeypatch, tmp_path):
    fake_exe = tmp_path / "BuferaMakineEkrani.exe"
    fake_exe.write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe), raising=False)

    base = app_paths.app_base_dir()

    assert base == tmp_path
