# SESSION_BRIEF - Son guncelleme: 2026-09-22

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**Manuel sayfa: "Başlangıç Konumuna Dön" satırı yamukluğu düzeltildi
(2026-09-22, kullanıcı ekran görüntüsü).** X kartındaki buton (64px sabit)
ile Y kartındaki "BAŞLANGIÇ KONUMU" kutusu (72px doğal) farklı yükseklikte
olduğu için bu satırdan sonraki her şey (Actual Position, Servo) X/Y
arasında 8px kaymıştı. İkisi artık `setFixedHeight` ile aynı yüksekliğe
(72px) sabitleniyor - ekran görüntüsü + widget geometrisiyle doğrulandı.
Öncesinde aynı seansta: H20-H22 (C6 teslimi, 17 numaralı görev) + U01-U11
Start engellerinin ana ekran alarm tablosuna canlı (kalıcı olmayan) satır
olarak eklenmesi + `[Uxx]` kod önekleri. Detay: CHANGELOG_MEMORY.md üstteki
4 giriş.

## Siradaki Gorevler

- [ ] PLC tarafı: H20-H22 ve daha önceki H12-H15/U06 aday tag'lerini
      build/export edip online doğrulamalı; sonra gerçek `config/opcua.json`'a
      eklenecek.
- [ ] Kullanıcı: gerçek PLC'de yeni HATA/UYARI davranışını test etmeli.
- [ ] PLC tarafı: MANUAL_RETURN_STOP (140)'tan Reset ile çıkış kararı
      hâlâ bekleniyor (13 numaralı bulgu).
- [ ] VisionCut 07/08/09 mesajları bekliyor ("sonra ilgilenelim").
- [ ] `data/bufera.db` paylaşımlı-engine test-izolasyonu kararı bekliyor
      (SettingsStore + AlarmRepository etkileniyor).
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 267/267 (2026-09-22).

## Son Degisiklikler

- 2026-09-22 - Manuel sayfa: "Başlangıç Konumuna Dön" satırı X/Y arasında
  8px yamuktu (HoldButton 64px vs ProcessStatusCard 72px), setFixedHeight
  ile eşitlendi.
- 2026-09-22 - U01-U11 ana ekran alarm tablosuna canlı (kalıcı olmayan)
  satırlar olarak eklendi; banner'a `[Uxx]` kod öneki eklendi.
- 2026-09-22 - PLC-HMI-20260922-17: H20/H21/H22 (3 yeni aday latched HATA).
- 2026-09-21 - PLC-HMI-20260921-14/15/16: Hata/Uyarı/Mesaj kataloğu,
  Reset bug fix, çoklu Start engelleri.

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler izole config
  kullanmali. `data/bufera.db` PAYLAŞIMLI - testler izole ETMİYOR; test
  sonrası `alarm_events` kirliliğini elle temizle (`DELETE FROM
  alarm_events`), `engineering_settings`'e DOKUNMA.
- Vision simülatörü PLC state/sensör/motion/valf taglarına ASLA yazmaz.
- Yeni, online doğrulanmamış PLC NodeId'sini gerçek `config/opcua.json`'a
  eklemeden önce PLC tarafının online doğrulamasını bekle (C0.4/C5 dersi).
- Gerçek PLC export dosyaları proje dışında (`C:\Users\agedik\Documents\
  ChatGPT\Bufera Tekstil PLC\...\plc_export\`) - kullanıcı yolu verirse
  doğrudan incelenebilir (büyük XML, chunk ile).
- VisionCut'ın gerçek mesaj kanalı `muratturan19/Brode_Vision_PLC` (dış
  repo) - bizim `visioncut_message/` klasörümüz onun el ile senkronlanan
  bir aynası, otomatik güncellenmiyor.
