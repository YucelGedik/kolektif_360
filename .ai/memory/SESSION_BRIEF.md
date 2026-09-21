# SESSION_BRIEF - Son guncelleme: 2026-09-21

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**PLC-HMI-20260921-14/15/16 (Hata/Uyarı/Mesaj kataloğu) TAMAMLANDI - bu
oturumun en büyük paketi.** Üç mesaj birlikte:
1. **Gerçek bug fix:** `request_reset()` artık gerçek modda `_alarms.
   clear_active()` çağırmıyor - Reset kabul edilmeden aktif HATA
   kaybolmuyor; temizlik yalnız PLC'nin kendi okuması FALSE olunca.
2. Yeni `ALARM_CATALOG`/`_update_alarm_conditions` (H01-H19) - PLC'nin
   latched bitlerinden rising/falling edge ile alarm kaydı üretir/kapatır.
   H12-H15 (5 aday tag) hazır ama PLC henüz build/export etmedi.
3. `active_alarm_count()` - ana ekran ALARM sayacı artık gerçek aktif
   HATA listesinden (hayali `alarm_count` değil).
4. `compute_start_inhibit_reasons` yeniden yazıldı - ilk engelde return
   etmiyor, U01-U11 tüm UYARI'ları birlikte listeliyor.
5. Manuel sayfa: move-to-start "stopping" durumu + Error önceliği + H05
   alarm mesajı tam yönlendirme metni içeriyor.
Yan bulgu: yerel `data/bufera.db`'de `code` sütunu fiziksel NOT NULL'dı,
düzeltildi (veri kaybı yok). Detay: CHANGELOG_MEMORY.md en üst giriş.

**Aynı gün, önceki tamamlanan işler (kronolojik, detay CHANGELOG_MEMORY.md):**
PLC-HMI-20260921-09 (Aşağı talepleri) -> C0.4 takibi -> PLC-HMI-20260921-
10/11 (C5) -> UI geri bildirimi -> C5 config fix (12) -> MANUAL_RETURN_STOP
sıkışma bulgusu + Busy/Aborted önceliği (13) -> bugünkü katalog (14/15/16).

**Ayrı bulgu (beklemede):** VisionCut'tan 3 yeni mesaj (07/08/09) - ayrı
süreç mimarisi, paketlenmiş exe, build sahipliği. Kullanıcı: "sonra
ilgilenelim" - dokunulmadı.

## Siradaki Gorevler

- [ ] Kullanıcı: gerçek PLC'de yeni HATA/UYARI davranışını test etmeli
      (Reset'in artık aktif alarmı yanlışlıkla temizlemediğini, çoklu
      Start uyarılarının birlikte göründüğünü doğrulamak).
- [ ] "Başlangıç Konumuna Dön" ve manuel Aşağı butonları hâlâ genel
      online doğrulama bekliyor (bkz. önceki 12/13 girişleri).
- [ ] PLC tarafı: MANUAL_RETURN_STOP (140)'tan Reset ile de çıkılabilir
      bir yol olmalı mı kararı hâlâ bekleniyor (13 numaralı bulgu).
- [ ] VisionCut 07/08/09 mesajları bekliyor.
- [ ] H4 (artık büyük ölçüde 14/15/16 ile kapandı) - PLC C2 kalan açık
      maddeleri (C6.2, C7) ayrı PLC işleri, bizim kapsamımız dışında.
- [ ] SettingsStore/AlarmRepository `data/bufera.db` test-izolasyonu
      kararı bekliyor - artık yalnız Settings değil, alarm motoru da
      neredeyse her fault-testinde şu an paylaşımlı gerçek DB'ye yazıyor
      (bilinen sorun büyüdü, karar hâlâ kullanıcıda).
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 256/256 (2026-09-21).

## Son Degisiklikler

- 2026-09-21 - PLC-HMI-20260921-14/15/16: Hata/Uyarı/Mesaj kataloğu,
  Reset bug fix, çoklu Start engelleri (detay: CHANGELOG_MEMORY.md).
- 2026-09-21 - MANUAL_RETURN_STOP (140) sıkışma bulgusu + Busy/Aborted
  öncelik düzeltmesi (PLC-HMI-20260921-13).
- 2026-09-21 - PLC-HMI-20260921-12: C5 gerçek config eksiği.
- 2026-09-21 - Manuel sayfa UI geri bildirimi + PLC-HMI-20260921-10/11
  ("Başlangıç Konumuna Dön") + C0.4 takibi + PLC-HMI-20260921-09.

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler izole config
  kullanmali. `data/bufera.db` PAYLAŞIMLI - testler izole ETMİYOR; artık
  hem SettingsStore hem AlarmRepository (yeni alarm motoru) etkileniyor -
  test sonrası `data/bufera.db`'deki `alarm_events` kirliliğini elle
  temizlemeyi unutma (`DELETE FROM alarm_events`), `engineering_settings`'e
  DOKUNMA (gerçek kullanıcı ayarları olabilir).
- Vision simülatörü PLC state/sensör/motion/valf taglarına ASLA yazmaz.
- Yeni, online doğrulanmamış PLC NodeId'sini gerçek `config/opcua.json`'a
  eklemeden önce PLC tarafının online doğrulamasını bekle (C0.4/C5 dersi).
- Gerçek PLC export dosyaları proje dışında (`C:\Users\agedik\Documents\
  ChatGPT\Bufera Tekstil PLC\...\plc_export\`) - kod/tag sorusu şüpheliyse
  kullanıcı yolu verirse doğrudan incelenebilir (büyük XML, chunk ile).
- VisionCut'ın gerçek mesaj kanalı `muratturan19/Brode_Vision_PLC` (dış
  repo) - bizim `visioncut_message/` klasörümüz onun el ile senkronlanan
  bir aynası, otomatik güncellenmiyor.
