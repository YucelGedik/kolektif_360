"""Two programs, one panel: the handover has to actually happen.

KARARLAR.md #1 put VisionCut in its own process. That turned "show the camera
page" into "put another program's window in front of the operator", and the
risk moved with it: a button that is wired to nothing looks exactly like a
button that works, because the page it used to switch to is gone either way.

So these tests do not ask whether `companion.py` can raise a window. They ask
whether pressing KAMERA EKRANI on the real nav bar reaches it.
"""

from __future__ import annotations

import json

import pytest
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from app import companion
from app.main import MainWindow
from services.machine_service import MachineService


def _window(tmp_path, vision_exe: str = "") -> MainWindow:
    cfg = tmp_path / "opcua.json"
    cfg.write_text(json.dumps({"endpoint": "", "vision_exe": vision_exe,
                               "nodes": {}}), encoding="utf-8")
    return MainWindow(MachineService(config_path=cfg))


# -- the wiring ------------------------------------------------------------

def test_camera_button_hands_over_instead_of_switching_pages(tmp_path, monkeypatch):
    win = _window(tmp_path, vision_exe=r"C:\Operon\VisionCut\OperonVisionCut.exe")
    win._navigate("settings")
    asked: list[str] = []
    monkeypatch.setattr("app.main.show_vision_screen",
                        lambda path, *a, **k: asked.append(str(path)) or "raised")
    monkeypatch.setattr(type(win), "showMinimized", lambda self: None)

    win._nav.button("camera").click()

    assert asked == [r"C:\Operon\VisionCut\OperonVisionCut.exe"], \
        "KAMERA EKRANI butonu companion'a hiç ulaşmıyor"
    assert win._stack.currentWidget() is win._settings_page, \
        "devretme sayfayı değiştirmemeli"


def test_the_exe_path_comes_from_the_config(tmp_path, monkeypatch):
    win = _window(tmp_path, vision_exe=r"D:\baska\yer\OperonVisionCut.exe")
    seen: list[str] = []
    monkeypatch.setattr("app.main.show_vision_screen",
                        lambda path, *a, **k: seen.append(str(path)) or "raised")
    monkeypatch.setattr(type(win), "showMinimized", lambda self: None)

    win._hand_over_to_vision()

    assert seen == [r"D:\baska\yer\OperonVisionCut.exe"]


def test_we_step_aside_only_when_there_is_something_to_reveal(tmp_path, monkeypatch):
    """Minimising with VisionCut absent strands the operator on the desktop.

    The kiosk has no taskbar: there would be no way back.
    """
    win = _window(tmp_path)
    minimised: list[bool] = []
    monkeypatch.setattr(type(win), "showMinimized",
                        lambda self: minimised.append(True))

    monkeypatch.setattr("app.main.show_vision_screen", lambda *a, **k: "missing")
    assert win._hand_over_to_vision() == "missing"
    assert minimised == [], "kamera ekranı yokken kendimizi küçültmemeliyiz"

    monkeypatch.setattr("app.main.show_vision_screen", lambda *a, **k: "launched")
    win._hand_over_to_vision()
    assert minimised == [True]


def test_the_placeholder_camera_page_is_gone(tmp_path):
    """Ayrı süreçte yer tutucunun karşılığı yok (VisionCut mesaj 08, kusur c)."""
    win = _window(tmp_path)
    assert "camera" not in win._pages
    assert win._stack.currentWidget() is win._machine_page, \
        "program makine ana sayfasıyla açılmalı"
    assert not hasattr(__import__("app.main", fromlist=["x"]),
                       "CameraPlaceholderPage")


# -- the mechanism ---------------------------------------------------------

def test_a_running_window_is_raised_not_launched(monkeypatch):
    raised: list[int] = []
    monkeypatch.setattr(companion, "_find_window", lambda hint: 4242)
    monkeypatch.setattr(companion, "_bring_to_front", lambda hwnd: raised.append(hwnd))

    def _explode(*_a, **_k):
        raise AssertionError("çalışan pencere varken ikinci kopya başlatıldı")

    monkeypatch.setattr(companion.subprocess, "Popen", _explode)
    assert companion.show_vision_screen(r"C:\yok\OperonVisionCut.exe") == "raised"
    assert raised == [4242]


def test_a_closed_program_is_launched(tmp_path, monkeypatch):
    exe = tmp_path / "OperonVisionCut.exe"
    exe.write_bytes(b"")
    started: list[list[str]] = []
    monkeypatch.setattr(companion, "_find_window", lambda hint: None)
    monkeypatch.setattr(companion.subprocess, "Popen",
                        lambda args, **k: started.append(args))

    assert companion.show_vision_screen(exe) == "launched"
    assert started == [[str(exe)]]


def test_launch_is_detached_so_it_outlives_us(tmp_path, monkeypatch):
    exe = tmp_path / "OperonVisionCut.exe"
    exe.write_bytes(b"")
    seen: dict = {}
    monkeypatch.setattr(companion, "_find_window", lambda hint: None)
    monkeypatch.setattr(companion.subprocess, "Popen",
                        lambda args, **k: seen.update(k))

    companion.show_vision_screen(exe)
    assert seen.get("creationflags", 0) != 0 or not companion._IS_WINDOWS


def test_an_unconfigured_or_missing_exe_says_missing(monkeypatch):
    monkeypatch.setattr(companion, "_find_window", lambda hint: None)
    assert companion.show_vision_screen("") == "missing"
    assert companion.show_vision_screen(r"C:\hicbir\yerde\yok.exe") == "missing"


def test_second_copy_knows_it_is_second():
    """İki kopya iki OPC UA oturumu açar ve aynı etiketlere yazar."""
    if not companion._IS_WINDOWS:
        pytest.skip("adlandırılmış mutex yalnız Windows'ta")
    name = "Local\\BuferaTestSingleInstance"
    first = companion.SingleInstance(name)
    try:
        assert first.is_first is True
        second = companion.SingleInstance(name)
        try:
            assert second.is_first is False
        finally:
            second.release()
    finally:
        first.release()


def test_our_own_title_still_carries_the_agreed_substring():
    """VisionCut bizi bu alt dizeyle buluyor (mesaj 08.2) - değiştirilemez."""
    assert companion.OWN_TITLE_HINT == "Makine Ekran"
    assert companion.VISION_TITLE_HINT == "Operon VisionCut"
