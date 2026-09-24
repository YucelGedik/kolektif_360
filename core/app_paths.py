"""Resolves the base directory config/data files live under.

VisionCut mesaj 08 (madde b, `INTEGRATION.md`): `persistence/db.py` ve
`plc/tag_map.py`'deki `Path(__file__).resolve().parent.parent` her zaman
proje kök dizinini varsayıyordu - PyInstaller ile paketlenmiş (frozen) bir
`.exe`de bu, geçici/salt-okunur bir açılım (extraction) dizinine düşer:
`config/opcua.json` hiç bulunamaz, `data/bufera.db` yazılamaz. Frozen
çalışırken bunun yerine .exe'nin BULUNDUĞU klasör kullanılır - taşınabilir
("xcopy") bir dağıtım için config/data klasörleri .exe ile aynı yerde,
görünür ve düzenlenebilir kalır."""

from __future__ import annotations

import sys
from pathlib import Path


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent
