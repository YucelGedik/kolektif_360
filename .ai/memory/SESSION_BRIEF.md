# SESSION_BRIEF - Son guncelleme: 2026-09-21

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**PLC-HMI-20260921-09 (manuel Aşağı talepleri) + C0.4 takibi TAMAMLANDI.**
PLC, `xBladeDownRequest`/`xClampDownRequest`/`xAlarmStopRequest`/
`xManualPreparationRequired`'ı Symbol Configuration'da yayımladığını
doğruladı - 4 NodeId gerçek `config/opcua.json`'a eklendi. Manuel sayfada
dört pulse buton (Yukarı+Aşağı × bıçak+baskı), ortak izin kontrolünden
geçiyor (`MachineService._pneumatic_common_allowed`: MANUAL + xManualMode +
xEmergencyOK + NOT alarmStopRequest/motionStop + eksenler durmuş + jog
bırakılmış); Aşağı ek şartlı (hazırlık kilidi + besleme kapalı).
`blade/clamp_down_tags_configured()` - tag eksikse buton hem devre dışı
kalır hem tıklansa bile göndermez. Gerçek OPC yazma reddi artık
`commandWriteError` ile UI'ya taşınıyor ("HATA — PLC REDDETTİ" + uyarı
kutusu). Valf komutlarına hâlâ hiç yazılmıyor. Detay: RULES.md,
CHANGELOG_MEMORY.md (2026-09-21, iki giriş).

**Ayrı bulgu:** `visioncut_message/` kanalına (kamera ekibi, dış repo
`muratturan19/Brode_Vision_PLC`'nin yerel aynası) 06 numaralı mesajla
endpoint+security mode+node haritası cevaplandı, pushlandı.

## Siradaki Gorevler

- [ ] Kullanıcı: masa/saha testiyle Aşağı butonlarını gerçek PLC'ye karşı
      doğrulamalı (config+kod hazır - online deneme kaldı).
- [ ] H4/H5/H7: PLC C2 (alarm)/C5 (Başlangıç Konumu) kararı gelince
      başlanacak (H7 iptal edildi).
- [ ] SettingsStore `data/bufera.db` test-izolasyonu kararı bekliyor.
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 211/211 (2026-09-21).

## Son Degisiklikler

- 2026-09-21 - C0.4 takibi: gerçek config'e 4 NodeId, eksik-tag koruması,
  gerçek OPC yazma reddinin UI'ya taşınması.
- 2026-09-21 - PLC-HMI-20260921-09: manuel Aşağı talepleri.
- 2026-09-21 - `visioncut_message/`e endpoint/node haritası mesajı (06).
- 2026-09-20 - Bench-test Vision Simülatörü + BadTypeMismatch kalıcı
  çözümü + alarm panosu + bıçak/baskı Geri Çek tek commit'te pushlandı.

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler izole config
  kullanmali. `data/bufera.db` PAYLAŞIMLI - testler izole ETMİYOR (bilinen).
- Vision simülatörü PLC state/sensör/motion/valf taglarına ASLA yazmaz.
- Yeni, online doğrulanmamış PLC NodeId'sini gerçek `config/opcua.json`'a
  eklemeden önce PLC tarafının online doğrulamasını bekle.
