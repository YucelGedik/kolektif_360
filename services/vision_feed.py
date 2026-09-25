"""VisionCut'ın yayınladığı canlı kare ve Start kararı (kanal mesajı 19, 22 §8).

VisionCut ayrı bir süreç (INTEGRATION.md, 2026-09-23 kararı). Operatör bu
ekranda Start'a basarken VisionCut'ın ekranı arkada kalıyor; kesim çizgisinin
kamera çerçevesinde olup olmadığını kimse görmüyordu. VisionCut artık iki dosya
yazıyor ve her birini atomik olarak değiştiriyor:

* ``kare.jpg``   -- 640 px genişliğinde kare; referans, ±çerçeve ve merkez
  çizgisi VisionCut tarafından çizilmiş (çerçeve VisionCut'ın kendi hizalama
  sınırı, burada yeniden hesaplanmaz);
* ``durum.json`` -- ``baslat_izni`` (bool), ``neden`` (operatör metni),
  ``sapma_mm``, ``cerceve_mm``, ``kesimde`` ve UTC ``zaman``.

Bu modül yalnız okur ve yaşını ölçer. Karar VisionCut'ındır; bayat ya da eksik
dosya "izin yok" demektir -- görüntü yoksa kilit açılmaz (mesaj 19 kararı).

⚠️ Bu kilit yalnız bu ekrandaki START düğmesini tutar. Paneldeki fiziksel
START'ı kapsamaz; PLC'nin state 40 kamera kontrolü her iki yolda da geçerli
(mesaj 22 §8).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

#: VisionCut'ın kurulu hâlde yazdığı klasör. Ortam değişkeniyle değiştirilebilir.
DEFAULT_FOLDER = Path(os.environ.get(
    "VISIONCUT_CANLI_DIR", r"C:\ProgramData\operon_visioncut\canli"))
#: VisionCut kesim dışında saniyede 4, kesimde saniyede 1 yazar. 2 s sessizlik
#: programın kapandığı ya da takıldığı anlamına gelir.
MAX_AGE_S = 2.0


@dataclass(frozen=True)
class VisionFeedState:
    fresh: bool              # durum dosyası var ve yeni
    allowed: bool            # VisionCut Start'a izin veriyor VE dosya taze
    reason: str              # operatöre gösterilecek metin
    cutting: bool            # VisionCut kesimde diyor
    picture: Path | None     # gösterilecek kare, yoksa None
    picture_mtime: float     # kare değişti mi diye bakmak için


class VisionFeedReader:
    def __init__(self, folder: Path = DEFAULT_FOLDER, max_age_s: float = MAX_AGE_S,
                 clock=time.time) -> None:
        self._folder = Path(folder)
        self._max_age_s = float(max_age_s)
        self._clock = clock

    def read(self) -> VisionFeedState:
        state_path = self._folder / "durum.json"
        picture_path = self._folder / "kare.jpg"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            stamp = datetime.fromisoformat(state["zaman"]).timestamp()
        except (OSError, ValueError, KeyError, TypeError):
            return VisionFeedState(False, False, "VisionCut görüntüsü yok "
                                   "(program kapalı olabilir).", False, None, 0.0)
        try:
            picture_mtime = picture_path.stat().st_mtime
            picture = picture_path
        except OSError:
            picture_mtime, picture = 0.0, None

        age = self._clock() - stamp
        if age > self._max_age_s:
            return VisionFeedState(False, False, f"VisionCut yanıt vermiyor "
                                   f"({age:.0f} s).", False, picture, picture_mtime)
        allowed = bool(state.get("baslat_izni", False))
        reason = str(state.get("neden") or ("Kamera onayı var." if allowed
                                            else "Kamera onayı yok."))
        return VisionFeedState(True, allowed, reason, bool(state.get("kesimde", False)),
                               picture, picture_mtime)
