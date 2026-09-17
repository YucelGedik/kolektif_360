# SESSION_BRIEF - Son guncelleme: 2026-09-16

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**Faz 8 - HMI/PLC entegrasyonu (docs/BUFERA_HMI_PLC_ENTEGRASYON_GOREV_PLANI.md)**

Kullanici gercek PLC'ye bagli; Faz 2 (Start/Stop/Reset/Jog/Manual-Auto) ve
Faz 4 (Ayarlar, gercek `lr*`/`t*` parametreleri, gercek default'lar) dogrulandi.
Bu turda 2 guvenlik onlemi eklendi: xCycleActive iken Muhendislik erisimi
kapatildi + cross-parameter validation (X/Y limit tutarliligi).

## Siradaki Gorevler

- [ ] Kullanici bu 2 guvenlik onlemini gercek PLC'de test edip bildirecek.
- [ ] Faz 3: Blade/Clamp manuel *Request tag'leri + Y merkez (plan SS6).
- [ ] Faz 5-6: Alarm engine (edge-based) + Vision Simulator ekrani.
- [ ] Pnomatik gecikmeler + Vision Zaman Asimi: Logic_Control'da hala hard-
      coded, GVL parametresi yok - Settings listesine hic alinmadi (kasitli).

## Son Build/Test

- `pytest`: 46/46 gecti (2026-09-16, guvenlik onlemleri sonrasi).

## Son Degisiklikler

- 2026-09-16 - 2 guvenlik onlemi eklendi (kullanici istegi):
  (1) `SettingsPage`: `snap.cycle_active` iken Muhendislik Erisimini Ac hem
  acilamiyor hem de zaten acikken devreye girerse zorla kapatilip uyari
  gosteriliyor. (2) `MachineService._validate_cross_field`: lrX_CutStartPos
  < lrX_CutEndPos, lrY_SoftwareMin < lrY_CenterPosition < lrY_SoftwareMax,
  lrY_SoftwareMin < lrY_SoftwareMax - ihlal varsa `set_parameter` OPC UA
  write'a hic gitmeden ValueError firlatir (UI zaten bunu gosteriyordu).
- 2026-09-16 - Ayarlar ekrani ust uste 3 gercek PLC hatasi bulup duzeltti:
  yazma sessizce eski degere donuyordu (write-confirm mekanizmasi), Uygula
  tiklaminda odak kaymasi degeri siliyordu (dirty-flag, hasFocus() degil),
  Y Yazılım Max spinbox araligi gercek degeri (30) 24'e kirpiyordu.
- 2026-09-16 - Faz 2 + Faz 4 kullanici tarafindan gercek PLC'de dogrulandi.

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md` okunur.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler bu dosyaya
  guvenmemeli, izole config ile test edin (`tests/test_tag_map.py` ornegi).
- `visioncut_message/` = paylasilan public kanalin yerel aynasi; kural 3'e
  (musteri/makine adi paylasilmaz) dikkat.
