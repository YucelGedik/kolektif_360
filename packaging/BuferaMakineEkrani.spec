# -*- mode: python ; coding: utf-8 -*-
# Build: .venv\Scripts\pyinstaller.exe packaging\BuferaMakineEkrani.spec
# (proje kökünden çalıştırın - .venv'de `pip install pyinstaller` gerekir).
# Çıktı: dist\BuferaMakineEkrani\BuferaMakineEkrani.exe (bkz. README.md).

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(PROJECT_ROOT, "app", "main.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BuferaMakineEkrani',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
