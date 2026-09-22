# SESSION_BRIEF - Son guncelleme: 2026-09-22

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**PLC-HMI-20260922-18 (C06_1 audit, `.ai/HMI_C061_AUDIT_TASK_20260922.md`)
TAMAMLANDI - A01-A06 hepsi uygulandı.** Başka bir ajanın HMI kaynak
denetimi; her madde kodda doğrulandıktan sonra düzeltildi (uydurma yoktu):
- **A01** `set_parameter` artık ortak bir izin kapısından geçiyor
  (stale/bağlantı [gerçek modda] + cycle_active + jog + eksen hareketi) -
  eskiden yalnız move_to_start_busy kontrol ediliyordu.
- **A02** Restart sonrası alarm uzlaştırması: `AlarmEvent`'e yeni
  `catalog_id` sütunu (migration), servis ilk gerçek okumada DB'deki hâlâ
  açık kayıtlarla RAM'i uzlaştırıyor (eskiden restart sonrası bir alarm ya
  hiç kapanmıyor ya da kopyalanıyordu). Aktif sayaç/liste artık SINIRSIZ
  (`active_events()`), 100'lük geçmiş sınırına bağlı değil.
- **A03** `compute_start_inhibit_reasons`: stale kontrolü artık start_
  permitted'DEN ÖNCE (eski sıra: bayat+eski-TRUE-izin kombinasyonunda U10
  hiç görünmüyordu).
- **A04** Alarmlar sayfasına dinamik "online doğrulama bekleyen kodlar"
  banner'ı - config'ten canlı okunur (H12-H15/H20-H22/U06).
- **A05** M01-M09 artık ana ekran tablosunda canlı (M08 özel: yalnız
  move_to_start "done" olduğu İLK tick'te, tek seferlik).
  M01-M07/M09 cycle_state süresince görünür.
- **A06** State etiket düzeltmeleri (140 "Durduruluyor" - PLC'nin kendi
  13 numaralı bulgusuyla uyumlu artık; 510 "Recovery" yerine PLC'nin 18
  Eylül talimatındaki "Manuel Hazırlık Bekleniyor" - **bunlar benim daha
  önceki oturumlarda attığım hatalardı**), `_pneumatic_common_allowed`'a
  operator_stop_active eklendi, U05/build-export yorum düzeltmeleri.

Öncesinde aynı seansta: H20-H22 (C6 teslimi, 17), U01-U11'in ana ekran
tablosuna canlı satır olarak eklenmesi, manuel sayfa yükseklik düzeltmesi.
Detay: CHANGELOG_MEMORY.md üstteki girişler.

## Siradaki Gorevler

- [ ] PLC tarafı: H12-H15/H20-H22/U06 (8 aday tag, export'ta var) online
      node/erişim testi yapmalı; sonra gerçek `config/opcua.json`'a
      eklenecek (Alarmlar sayfasında artık bunları listeleyen canlı bir
      banner var - A04).
- [ ] Kullanıcı: gerçek PLC'de yeni HATA/UYARI/MESAJ davranışını ve A01-A06
      düzeltmelerini test etmeli.
- [ ] PLC tarafı: MANUAL_RETURN_STOP (140)'tan Reset ile çıkış kararı
      hâlâ bekleniyor (13 numaralı bulgu).
- [ ] VisionCut 07/08/09 mesajları bekliyor ("sonra ilgilenelim").
- [ ] `data/bufera.db` paylaşımlı-engine test-izolasyonu kararı bekliyor.
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 305/305 (2026-09-22).

## Son Degisiklikler

- 2026-09-22 - PLC-HMI-20260922-18 (C06_1 audit, A01-A06): ayar yazma izni,
  restart alarm uzlaştırması, U10 sıralaması, eksik-tag banner'ı, M01-M09
  canlı, state etiket düzeltmeleri (140/510 - kendi hatalarımdı).
- 2026-09-22 - Manuel sayfa 8px yamukluk (HoldButton/ProcessStatusCard
  yükseklik farkı) + U01-U11 canlı tablo satırları + [Uxx] kod önekleri.
- 2026-09-22 - PLC-HMI-20260922-17: H20/H21/H22 (3 yeni aday latched HATA).

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler izole config
  kullanmali. `data/bufera.db` PAYLAŞIMLI - testler izole ETMİYOR; tam
  suite tek çalıştırmada ~4 satır kirlilik üretiyor (DemoSimulator'ın
  vision-heartbeat alarmı, kod=1201 - GERÇEK PLC verisi DEĞİL, saf test
  yan etkisi). Test sonrası `DELETE FROM alarm_events` ile TAMAMI
  temizlenebilir (code IS NULL/IS NOT NULL ayrımı yapmaya gerek yok -
  ikisi de sentetik). `engineering_settings`'e DOKUNMA.
- Vision simülatörü PLC state/sensör/motion/valf taglarına ASLA yazmaz.
- Yeni, online doğrulanmamış PLC NodeId'sini gerçek `config/opcua.json`'a
  eklemeden önce PLC tarafının online doğrulamasını bekle (C0.4/C5 dersi).
- Gerçek PLC export dosyaları proje dışında (`C:\Users\agedik\Documents\
  ChatGPT\Bufera Tekstil PLC\...\plc_export\`) - kullanıcı yolu verirse
  doğrudan incelenebilir (büyük XML, chunk ile).
- VisionCut'ın gerçek mesaj kanalı `muratturan19/Brode_Vision_PLC` (dış
  repo) - bizim `visioncut_message/` klasörümüz onun el ile senkronlanan
  bir aynası, otomatik güncellenmiyor.
