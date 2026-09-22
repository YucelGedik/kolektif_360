# SESSION_BRIEF - Son guncelleme: 2026-09-22

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**PLC-HMI-20260922-17 (C6 toplu teslim, H20/H21/H22) TAMAMLANDI.** PLC'nin
`.ai/HMI_C6_FINAL_TASK_20260922.md` ile ilettiği 3 yeni aday latched HATA
(mod değişimi/çevrim sırasında baskı kaybı/dönüşte bıçak açıklığı kaybı)
H12-H15 ile AYNI disiplinle eklendi: `MachineSnapshot` alanları False
varsayılan, `ALARM_CATALOG`'a H20-H22, yalnız `opcua.example.json`'a tag
(gerçek config'e PLC online doğrulayana kadar girmez), "Alarm Listesi"
sekmesine "henüz build/online doğrulama yapılmadı" notuyla eklendi. Detay:
CHANGELOG_MEMORY.md en üst giriş.

**Önceki (2026-09-22) - Alarmlar sayfası UI geri bildirimi TAMAMLANDI:**
Sekme metni okunmuyordu (QTabBar stil eksikliği), düzeltildi. Yeni "Alarm
Listesi" sekmesi (`core/notification_catalog.py`) - operatörün her Hata/
Uyarı/Mesaj'ın anlamını okuyabileceği statik referans. Detay: CHANGELOG_
MEMORY.md.

**Önceki (2026-09-21) - PLC-HMI-20260921-14/15/16 (Hata/Uyarı/Mesaj
kataloğu) TAMAMLANDI - en büyük paket:** Reset artık aktif HATA'yı
yanlışlıkla temizlemiyor (gerçek bug fix), yeni `ALARM_CATALOG`/`_update_
alarm_conditions` (H01-H19) rising/falling edge ile alarm üretir/kapatır,
`active_alarm_count()` gerçek veriye bağlandı, `compute_start_inhibit_
reasons` çoklu UYARI (U01-U11) listeliyor. Detay: CHANGELOG_MEMORY.md.

**Aynı hafta, önceki tamamlanan işler (kronolojik, detay CHANGELOG_
MEMORY.md):** PLC-HMI-20260921-09 (Aşağı talepleri) -> C0.4 takibi ->
PLC-HMI-20260921-10/11 (C5) -> UI geri bildirimi -> C5 config fix (12) ->
MANUAL_RETURN_STOP sıkışma bulgusu + Busy/Aborted önceliği (13) -> katalog
(14/15/16).

**Ayrı bulgu (beklemede):** VisionCut'tan 3 yeni mesaj (07/08/09) - ayrı
süreç mimarisi, paketlenmiş exe, build sahipliği. Kullanıcı: "sonra
ilgilenelim" - dokunulmadı.

## Siradaki Gorevler

- [ ] PLC tarafı: H20-H22 (`xAlarmModeChangedDuringCycle`/`xAlarmClamp
      LostDuringCycle`/`xAlarmBladeNotClearDuringReturn`) build/export
      edip online doğrulamalı; ardından gerçek `config/opcua.json`'a
      eklenecek (C6 toplu teslim, 17 numaralı görev).
- [ ] Kullanıcı: gerçek PLC'de yeni HATA/UYARI davranışını test etmeli
      (Reset'in artık aktif alarmı yanlışlıkla temizlemediğini, çoklu
      Start uyarılarının birlikte göründüğünü doğrulamak).
- [ ] "Başlangıç Konumuna Dön" ve manuel Aşağı butonları hâlâ genel
      online doğrulama bekliyor (bkz. önceki 12/13 girişleri).
- [ ] PLC tarafı: MANUAL_RETURN_STOP (140)'tan Reset ile de çıkılabilir
      bir yol olmalı mı kararı hâlâ bekleniyor (13 numaralı bulgu; C6
      teslimindeki genel FAULT yönlendirme notlarıyla ilişkili olabilir).
- [ ] VisionCut 07/08/09 mesajları bekliyor.
- [ ] SettingsStore/AlarmRepository `data/bufera.db` test-izolasyonu
      kararı bekliyor - artık yalnız Settings değil, alarm motoru da
      neredeyse her fault-testinde şu an paylaşımlı gerçek DB'ye yazıyor
      (bilinen sorun büyüdü, karar hâlâ kullanıcıda).
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 262/262 (2026-09-22).

## Son Degisiklikler

- 2026-09-22 - PLC-HMI-20260922-17: H20/H21/H22 (3 yeni aday latched
  HATA) - model/katalog/example config/Alarm Listesi, C0.4/C5 disiplini.
- 2026-09-22 - Alarmlar sayfası: "Alarm Listesi" referans sekmesi +
  sekme metni okunmuyordu (QTabBar stil eksikliği) düzeltildi.
- 2026-09-21 - PLC-HMI-20260921-14/15/16: Hata/Uyarı/Mesaj kataloğu,
  Reset bug fix, çoklu Start engelleri (detay: CHANGELOG_MEMORY.md).
- 2026-09-21 - MANUAL_RETURN_STOP (140) sıkışma bulgusu + Busy/Aborted
  öncelik düzeltmesi (PLC-HMI-20260921-13).

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
