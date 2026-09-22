# SESSION_BRIEF - Son guncelleme: 2026-09-22

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**GÜN SONU (2026-09-22) - tüm işler push'landı, oturum kapatıldı.**
`master` GitHub'a push edildi (`kolektif_360`, `35d7aec`'e kadar). VisionCut
tarafına repo güncellemesi bildirimi yazıldı (`visioncut_message/mesajlar/
2026-09-22_10_bufera.md` - yalnız yerel ayna, gerçek dış repoya (`muratturan
19/Brode_Vision_PLC`) senkron kullanıcı tarafından elle yapılmalı). PLC
tarafına da `.ai/Codex_Codesys.md`'de gün sonu özeti yazıldı. Bekleyen HMI
tarafı iş YOK - sıradaki adım PLC'nin online doğrulaması veya kullanıcının
sahada test etmesi.

**Bugün tamamlanan (kronolojik, detay CHANGELOG_MEMORY.md):** Hız
parametre sınırları gerçek mekaniğe göre revize edildi (6 alan) ->
PLC-HMI-20260922-18 (C06_1 audit, A01-A06: ayar yazma izni, restart alarm
uzlaştırması, U10 sıralaması, eksik-tag banner'ı, M01-M09 canlı mesajlar,
state 140/510 etiket düzeltmeleri - ikisi benim önceki hatalarımdı) ->
manuel sayfa 8px yamukluk + U01-U11 canlı tablo -> H20-H22 (17).

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
- [ ] Kullanıcı: `visioncut_message/mesajlar/2026-09-22_10_bufera.md`
      (repo güncelleme bildirimi) gerçek dış repoya (`muratturan19/Brode_
      Vision_PLC`) elle senkronlanmalı - biz oraya doğrudan yazamıyoruz.
- [ ] `data/bufera.db` paylaşımlı-engine test-izolasyonu kararı bekliyor.
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 306/306 (2026-09-22).

## Son Degisiklikler

- 2026-09-22 - Hız parametre sınırları gerçek mekaniğe göre revize edildi
  (6 alan, kullanıcı onaylı nihai limitler - `core/parameters.py`).
- 2026-09-22 - PLC-HMI-20260922-18 (C06_1 audit, A01-A06): ayar yazma izni,
  restart alarm uzlaştırması, U10 sıralaması, eksik-tag banner'ı, M01-M09
  canlı, state etiket düzeltmeleri (140/510 - kendi hatalarımdı).
- 2026-09-22 - Manuel sayfa 8px yamukluk + U01-U11 canlı tablo satırları.

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
