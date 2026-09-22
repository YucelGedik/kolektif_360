# SESSION_BRIEF - Son guncelleme: 2026-09-22

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**Hız parametre sınırları gerçek mekaniğe göre revize edildi (2026-09-22,
kullanıcı talebi - "mekaniğe bağlandık ve bu sınırlara karar verdik").**
`core/parameters.py`: X Kesim 1-800, X Dönüş 1-1060, Y Pozisyonlama 1-50,
Y Follow Maks. 1-50, X Jog 1-400, Y Jog 1-50 - artık tahmin değil, gerçek
onaylı mekanik limit. Detay: CHANGELOG_MEMORY.md üst giriş.

**Önceki (2026-09-22) - PLC-HMI-20260922-18 (C06_1 audit) TAMAMLANDI:**
Başka bir ajanın HMI kaynak denetimi, A01-A06 hepsi uygulandı (ayar yazma
izni, restart alarm uzlaştırması, U10 sıralaması, eksik-tag banner'ı,
M01-M09 canlı mesajlar, state 140/510 etiket düzeltmeleri - ikisi benim
önceki hatalarımdı). Öncesinde: H20-H22 (17), U01-U11 canlı tablo, manuel
sayfa yükseklik düzeltmesi. Detay: CHANGELOG_MEMORY.md.

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
