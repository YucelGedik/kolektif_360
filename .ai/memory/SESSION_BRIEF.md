# SESSION_BRIEF - Son guncelleme: 2026-09-21

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**PLC-HMI-20260921-10/11 (C5, "Başlangıç Konumuna Dön" tek buton) TAMAMLANDI,
online test bekliyor.** Eski "MERKEZE GİT / Y=0" kaldırıldı; tek buton 3
saniye kesintisiz basılı tutulunca X+Y'yi ayarlı başlangıç konumuna (lrX_
CutStartPos/lrY_CenterPosition) tek pulse (`xMoveToStartRequest`) ile
götürüyor. Erken bırakma/odak-sayfa kaybı/izin-stale/bağlantı kaybı anında
iptal eder; süre dolunca parmak basılı kalsa da tek pulse. İzin PLC'nin
`xMoveToStartAllowed`'ından okunur (HMI yeniden üretmez). Busy `xCycleActive`
DEĞİL - HMI jog/mod/pnömatik/ayar yazmalarını Busy'de AYRICA kilitler, Stop
hariç. Readback (Busy/Done/Aborted/Error) edge-detection ile izleniyor - eski
komuttan kalma stale/latched Done asla yeni sonuç sayılmaz. C5 node'ları
yalnız `config/opcua.example.json`'da - PLC henüz build/export etmedi.

**Önceki (aynı gün) - C0.4 takibi + PLC-HMI-20260921-09 (manuel Aşağı
talepleri) TAMAMLANDI.** 4 NodeId gerçek config'e eklendi, eksik-tag koruması
ve gerçek OPC yazma reddi UI'ya taşındı. Detay: RULES.md, CHANGELOG_MEMORY.md.

**Ayrı bulgu (beklemede, kullanıcı talimatı):** VisionCut tarafından 3 yeni
mesaj (07/08/09) geldi - ayrı süreç mimarisi kararı, paketlenmiş exe + 4
kusur yaması, pencere başlığı/build sahipliği soruları. Kullanıcı: "önce biz
işimizi bitirelim" - dokunulmadı, henüz bizim `visioncut_message/`
mirror'ımıza bile eklenmedi.

## Siradaki Gorevler

- [ ] Kullanıcı: masa/saha testiyle hem Aşağı butonlarını hem "Başlangıç
      Konumuna Dön"u gerçek PLC'ye karşı doğrulamalı (C5 node'ları henüz
      gerçek config'te değil - PLC build/export + online doğrulama sonrası
      eklenmeli, C0.4 emsaliyle aynı disiplin).
  - [ ] VisionCut 07/08/09 mesajları: kullanıcı "sonra ilgilenelim" dedi -
      beklemede.
- [ ] H4/H7: PLC C2 (alarm) kararı gelince başlanacak (H7 iptal edildi).
- [ ] SettingsStore `data/bufera.db` test-izolasyonu kararı bekliyor.
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 235/235 (2026-09-21).

## Son Degisiklikler

- 2026-09-21 - PLC-HMI-20260921-10/11: "Başlangıç Konumuna Dön" tek buton,
  3s basılı tutuş (detay: RULES.md, CHANGELOG_MEMORY.md aynı tarihli girişi).
- 2026-09-21 - C0.4 takibi: gerçek config'e 4 NodeId, eksik-tag koruması,
  gerçek OPC yazma reddinin UI'ya taşınması.
- 2026-09-21 - PLC-HMI-20260921-09: manuel Aşağı talepleri.
- 2026-09-21 - `visioncut_message/`e endpoint/node haritası mesajı (06).

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler izole config
  kullanmali. `data/bufera.db` PAYLAŞIMLI - testler izole ETMİYOR (bilinen).
- Vision simülatörü PLC state/sensör/motion/valf taglarına ASLA yazmaz.
- Yeni, online doğrulanmamış PLC NodeId'sini gerçek `config/opcua.json`'a
  eklemeden önce PLC tarafının online doğrulamasını bekle (C0.4/C5 dersi).
- VisionCut'ın gerçek mesaj kanalı `muratturan19/Brode_Vision_PLC` (dış
  repo) - bizim `visioncut_message/` klasörümüz onun periyodik el ile
  senkronlanan bir aynası, otomatik güncellenmiyor.
