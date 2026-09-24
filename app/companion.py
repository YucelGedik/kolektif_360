"""The other program on the same panel.

Two applications share the machine PC: this one and Operon VisionCut. They
were going to be one process; that was refused for a measured reason (VisionCut
message 07: a single plot removed from their process took vision from 26.9 to
35.1 fps, and their accuracy is made of frame rate). KARARLAR.md #1 records the
decision: separate processes, separate full-screen windows, and the switch
between them is a desktop problem rather than a protocol one.

Two rules make that survivable on a kiosk with no taskbar:

  * **Launch or raise, never just show.** An operator can close a window. A
    button that only raised an existing window would leave the other program
    gone until somebody found a keyboard. Starting it when it is missing makes
    the pair self-healing.
  * **One instance each.** A second copy of this program would open a second
    OPC UA session and write the same tags. The second launch raises the first
    window and exits.

Windows only. Everything degrades to "do nothing and say so" elsewhere, so a
Linux or macOS development box still runs.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

#: Substring matched against window titles when looking for VisionCut. Their
#: title is "Operon VisionCut v1.0.0-rc.23 (faz1-5)"; the product name is what
#: survives their version bumps, and they have undertaken not to change it
#: (VisionCut message 08, "Tek ricamız: pencere başlığı").
VISION_TITLE_HINT = "Operon VisionCut"

#: Our own title must keep containing "Makine Ekran" for the same reason, in
#: the other direction. See app/main.py.
OWN_TITLE_HINT = "Makine Ekran"

#: Named mutex for the single-instance check.
SINGLE_INSTANCE_NAME = "Local\\BuferaMakineEkrani.single"

_IS_WINDOWS = sys.platform.startswith("win")


def _find_window(title_hint: str) -> int | None:
    """Handle of the first visible top-level window whose title matches."""
    if not _IS_WINDOWS or not title_hint:
        return None
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    found: list[int] = []
    needle = title_hint.casefold()

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _visit(hwnd, _lparam):  # type: ignore[no-untyped-def]
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        if needle in buffer.value.casefold():
            found.append(int(hwnd))
            return False
        return True

    user32.EnumWindows(_visit, 0)
    return found[0] if found else None


def _bring_to_front(hwnd: int) -> None:
    """Restore if minimised, then ask for the foreground.

    ⚠️ The request can be refused. Windows grants the foreground only to a
    process that already owns it or was given it, which is why the program
    HANDING OVER minimises itself -- that is what actually puts the other one
    in front. This call is the polite half, not the load-bearing one.
    """
    if not _IS_WINDOWS:
        return
    import ctypes

    user32 = ctypes.windll.user32
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)       # SW_RESTORE
    user32.SetForegroundWindow(hwnd)


def show_vision_screen(exe_path: str | os.PathLike[str] | None,
                       title_hint: str = VISION_TITLE_HINT) -> str:
    """Bring VisionCut forward, starting it if it is not running.

    Returns what happened, for the log and for tests: ``"raised"``,
    ``"launched"``, ``"missing"`` (no path configured or file not found) or
    ``"failed"``.
    """
    hwnd = _find_window(title_hint)
    if hwnd is not None:
        _bring_to_front(hwnd)
        log.info("Kamera ekranı öne alındı")
        return "raised"

    if not exe_path:
        log.warning("Kamera ekranı çalışmıyor ve yolu tanımlı değil "
                    "(config/opcua.json içinde vision_exe)")
        return "missing"

    target = Path(exe_path)
    if not target.is_file():
        log.warning("Kamera ekranı bulunamadı: %s", target)
        return "missing"

    try:
        # Detached: VisionCut must outlive this process. As a child, closing
        # the machine screen would take the operator's camera screen with it.
        flags = 0
        if _IS_WINDOWS:
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008  # DETACHED
        subprocess.Popen([str(target)], cwd=str(target.parent),
                         creationflags=flags, close_fds=True)
    except OSError:
        log.exception("Kamera ekranı başlatılamadı: %s", target)
        return "failed"

    log.info("Kamera ekranı başlatıldı: %s", target)
    return "launched"


class SingleInstance:
    """A named mutex that says whether this process is the first copy.

    Held for the life of the process; Windows releases it when the process
    dies, including a crash, so a stale lock cannot strand the panel.
    """

    def __init__(self, name: str = SINGLE_INSTANCE_NAME) -> None:
        self._name = name
        self._handle = None
        self.is_first = True
        if not _IS_WINDOWS:
            return
        import ctypes

        kernel32 = ctypes.windll.kernel32
        self._handle = kernel32.CreateMutexW(None, False, name)
        # 183 = ERROR_ALREADY_EXISTS. The mutex is opened either way, so the
        # handle is valid; only the error code distinguishes the two cases.
        self.is_first = kernel32.GetLastError() != 183

    def release(self) -> None:
        if self._handle and _IS_WINDOWS:
            import ctypes

            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None


def raise_existing_instance(title_hint: str = OWN_TITLE_HINT) -> bool:
    """Put an already running copy of THIS program in front. True if found."""
    hwnd = _find_window(title_hint)
    if hwnd is None:
        return False
    _bring_to_front(hwnd)
    return True
