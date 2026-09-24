# -*- mode: python ; coding: utf-8 -*-
"""Tek klasorluk Windows paketi:  python -m PyInstaller --noconfirm --clean MakineEkrani.spec

Neden boyle:

* `sqlalchemy.dialects.sqlite` gizli import -- SQLAlchemy lehceyi calisma
  aninda, isimle yukler; PyInstaller'in statik analizi bunu goremez ve paket
  ilk veritabani erisiminde patlar.
* `collect_submodules('asyncua')` -- asyncua da kendi modullerini isimle
  cozuyor (ua tipleri, sunucu/istemci alt paketleri).
* `--add-data config;config` YOK, bilerek. Pakete gomulen bir yapilandirma,
  musterinin degistiremeyecegi bir yapilandirma olurdu; paketlenmis calisma
  `%ProgramData%\Bufera\MakineEkrani\config` altindan okuyor (app/paths.py).

Derledikten sonra exe'yi BOS BIR YAPILANDIRMAYLA bir kez calistirin -- temiz
bir makinede ilk acilis, yalnizca paketlenince gorunen kusurlarin cikti yer.
"""
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['sqlalchemy.dialects.sqlite']
hiddenimports += collect_submodules('asyncua')


a = Analysis(
    ['app\\main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='MakineEkrani',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MakineEkrani',
)
