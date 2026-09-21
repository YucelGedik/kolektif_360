# SESSION_BRIEF - Son guncelleme: 2026-09-21

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**PLC-HMI-20260921-09 (manuel bıçak/baskı Aşağı talepleri) uygulandı,
online test bekliyor.** `xBladeDownRequest`/`xClampDownRequest` (YENİ, PLC
tarafı henüz build/export etmedi) - Manuel sayfada artık dört pulse buton
var (Yukarı+Aşağı, bıçak+baskı). Dört buton da ortak, daha eksiksiz bir izin
kontrolünden geçiyor (`MachineService._pneumatic_common_allowed`: MANUAL +
xManualMode + xEmergencyOK + NOT alarmStopRequest/motionStop + eksenler
durmuş + jog bırakılmış); Aşağı'nın ek şartı var (hazırlık kilidi + besleme
kapalı). Aşağı'ya PLC-onaylı kabul biti YOK (bilinçli) - "Son Komut" kartı
Yukarı'da PLC kabulünü, Aşağı'da yalnız gönderimi (kanıt değil) gösterir.
2 yeni NodeId (`cmd_blade_down`/`cmd_clamp_down`) + 2 daha (`alarm_stop_
request`/`manual_preparation_required`) yalnız `config/opcua.example.json`'a
eklendi - GERÇEK `config/opcua.json`'a EKLENMEDİ (PLC henüz deploy etmedi,
online doğrulanmamış node canlı bağlantıyı bozabilir). `xEmergencyOK`/
`xMotionStop`/`FeedForwardPB`/`FeedReversePB` zaten doğrulanmış tag'ler
olduğu için gerçek config'e de eklendi.

**Önceki (2026-09-18) iş - PLC-HMI-20260918-04/06 + alarm panosu -
tamamlandı, detay CHANGELOG_MEMORY.md'de.** H4 (canlı alarm mapping)/H5
(Başlangıca Git) hâlâ PLC C2/C5 sözleşmesini bekliyor.

**Ayrı, bugkü bulgu:** `visioncut_message/` kanalına (kamera ekibiyle,
GitHub'da ayrı repo `muratturan19/Brode_Vision_PLC`'nin yerel aynası) 06
numaralı mesajla endpoint+security mode+node haritası cevaplandı ve
pushlandı - bu kanalın kendi Rule 3'ü (IP yazılmaz) kullanıcı onayıyla
bilinçli olarak aşıldı.

## Siradaki Gorevler

- [ ] Kullanıcı: PLC'yi build/export edip online sembolleri doğrulayınca
      4 yeni NodeId'yi gerçek `config/opcua.json`'a eklemeli, sonra masa/
      saha testi yapmalı (09 sözleşmesi).
- [ ] H4/H5/H7: PLC C2 (alarm sözleşmesi)/C5 (Başlangıç Konumuna Git) kararı
      gelince başlanacak (H7 iptal edildi).
- [ ] SettingsStore `data/bufera.db` test-izolasyonu kararı kullanıcıdan
      bekliyor (bilinen, çözülmedi).
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 204/204 (2026-09-21).

## Son Degisiklikler

- 2026-09-21 - PLC-HMI-20260921-09: manuel Aşağı talepleri (detay:
  RULES.md, CHANGELOG_MEMORY.md aynı tarihli girişi).
- 2026-09-21 - `visioncut_message/` kanalına endpoint/security mode/node
  haritası mesajı (06) eklendi ve pushlandı.
- 2026-09-20 - Bench-test Vision Simülatörü + BadTypeMismatch kalıcı
  çözümü + alarm panosu + bıçak/baskı Geri Çek tek commit'te pushlandı.

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler izole config
  kullanmali. `data/bufera.db` PAYLAŞIMLI - testler bunu izole ETMİYOR
  (bilinen, cozulmedi sorun).
- Vision simülatörü PLC state/sensör/motion/valf taglarına ASLA yazmaz.
- Yeni, online doğrulanmamış PLC NodeId'lerini gerçek `config/opcua.json`'a
  eklemeden önce iki kez düşün - bağlı bir makineye karşı çalışıyoruz.
