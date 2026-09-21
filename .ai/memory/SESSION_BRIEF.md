# SESSION_BRIEF - Son guncelleme: 2026-09-21

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**PLC-HMI-20260921-10/11 (C5, "Başlangıç Konumuna Dön") + kullanıcı UI
geri bildirimi TAMAMLANDI, online test bekliyor.** Tek buton 3 saniye
kesintisiz basılı tutulunca X+Y'yi ayarlı başlangıç konumuna tek pulse ile
götürüyor - erken bırakma/odak-sayfa kaybı/izin-stale/bağlantı kaybı anında
iptal eder, süre dolunca parmak basılı kalsa da tek pulse. İzin PLC'nin
`xMoveToStartAllowed`'ından okunur; Busy `xCycleActive` DEĞİL, HMI jog/mod/
pnömatik/ayar yazmalarını ayrıca kilitler (Stop hariç). Ekran görüntüsü
sonrası: buton X kartına taşındı (durum Y'de kaldı), hint butonun içinde
köşede, X-/Y- satırları `addStretch(1)` ile hizalandı, "JOG Yavaş/Hızlı"
kaldırılıp yerine `lr_x/y_jog_velocity` parametresine bağlı "Düzenle"
tik kutulu hız girişi geldi. C5 node'ları yalnız `config/opcua.example.json`
'da - PLC henüz build/export etmedi.

**Önceki (aynı gün) - C0.4 takibi + PLC-HMI-20260921-09 (manuel Aşağı
talepleri) TAMAMLANDI.** 4 NodeId gerçek config'e eklendi, eksik-tag koruması
ve gerçek OPC yazma reddi UI'ya taşındı. Detay: RULES.md, CHANGELOG_MEMORY.md.

**Ayrı bulgu (beklemede, kullanıcı talimatı):** VisionCut'tan 3 yeni mesaj
(07/08/09) geldi - ayrı süreç mimarisi, paketlenmiş exe + 4 kusur yaması,
pencere başlığı/build sahipliği. Kullanıcı: "önce biz işimizi bitirelim" -
dokunulmadı.

## Siradaki Gorevler

- [ ] Kullanıcı: masa/saha testiyle Aşağı butonlarını ve "Başlangıç Konumuna
      Dön"u gerçek PLC'ye karşı doğrulamalı (C5 node'ları henüz gerçek
      config'te değil - build/export + online doğrulama sonrası eklenmeli).
- [ ] VisionCut 07/08/09 mesajları: kullanıcı "sonra ilgilenelim" dedi.
- [ ] H4/H7: PLC C2 (alarm) kararı gelince başlanacak (H7 iptal edildi).
- [ ] SettingsStore `data/bufera.db` test-izolasyonu kararı bekliyor.
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 235/235 (2026-09-21).

## Son Degisiklikler

- 2026-09-21 - Manuel sayfa UI geri bildirimi: buton yerleşimi/hizalama +
  jog hızı girişi (detay: CHANGELOG_MEMORY.md aynı tarihli en üst girişi).
- 2026-09-21 - PLC-HMI-20260921-10/11: "Başlangıç Konumuna Dön" tek buton.
- 2026-09-21 - C0.4 takibi: gerçek config'e 4 NodeId, eksik-tag koruması.
- 2026-09-21 - PLC-HMI-20260921-09: manuel Aşağı talepleri.

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler izole config
  kullanmali. `data/bufera.db` PAYLAŞIMLI - testler izole ETMİYOR (bilinen).
- Vision simülatörü PLC state/sensör/motion/valf taglarına ASLA yazmaz.
- Yeni, online doğrulanmamış PLC NodeId'sini gerçek `config/opcua.json`'a
  eklemeden önce PLC tarafının online doğrulamasını bekle (C0.4/C5 dersi).
- VisionCut'ın gerçek mesaj kanalı `muratturan19/Brode_Vision_PLC` (dış
  repo) - bizim `visioncut_message/` klasörümüz onun el ile senkronlanan
  bir aynası, otomatik güncellenmiyor.
