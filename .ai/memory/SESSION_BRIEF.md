# SESSION_BRIEF - Son guncelleme: 2026-09-22

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**Alarm/Uyarı katalog çalışması TAMAMLANDI (2026-09-22 seansı).** Sırayla:
H20-H22 (PLC-HMI-20260922-17, C6 teslimi - 3 yeni aday latched HATA, H12-
H15 disipliniyle) eklendi; ardından kullanıcı ana ekrandaki "Start engelli"
banner'ının kodsuz olduğunu ve U01-U11'in hiç alarm tablosuna (Uyarı
filtresi) düşmediğini fark etti. İkisi de düzeltildi: banner'a `[Uxx]` kod
öneki + U01-U11 artık ana ekran tablosunda da CANLI satır olarak görünüyor
("ŞİMDİ"/PLC/[Uxx] mesaj) - ama `AlarmRepository`'ye YAZILMIYOR (Reset'ten
bağımsız, geçmişte iz bırakmaz, koşul kapanınca anında kaybolur - "alarm
yağmuru olmasın" hedefiyle bilinçli). Detay: CHANGELOG_MEMORY.md üstteki
3 giriş.

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
