# SESSION_BRIEF - Son guncelleme: 2026-09-21

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**ACİL, devam ediyor - Kullanıcı canlı PLC'de sıkıştı: MANUAL_RETURN_STOP
(140)'ta donuk kaldı.** "Başlangıç Konumuna Dön" sürerken Reset+Stop'a
basınca oluştu. Kullanıcının paylaştığı gerçek PLC export'unu inceledim,
PLC tarafı da bağımsız inceleyip yanıt verdi - şu ana kadar 2 HMI-tarafı
gösterim hatası bulundu ve düzeltildi:
1. `CycleState` enum'unda 130/140 hiç yoktu -> "Bilinmeyen Durum (140)"
   gösteriyordu. Eklendi + Türkçe etiketler.
2. **PLC'nin bulduğu gerçek hata:** Busy=TRUE iken Aborted=TRUE de
   olabiliyor (ara/duruş evresi) - HMI bunu "REDDEDİLDİ" diye BİTMİŞ bir
   sonuç gibi gösteriyordu. Düzeltildi: Busy TRUE olduğu sürece artık
   Done/Aborted/Error hiç okunmuyor.

**Hâlâ AÇIK:** 140'tan çıkışın asıl nedeni (aday: `xStopActive` anlık/
latch'siz sinyali, fiziksel Stop latch'liyse asla temizlenmez; Reset bu
state'e hiç etki etmiyor) - PLC tarafının canlı veriyle doğrulaması
bekleniyor. Kullanıcının makinesi muhtemelen HÂLÂ sıkışık durumda.

Detay: CHANGELOG_MEMORY.md en üst iki giriş.

**Aynı gün, önceki tamamlanan işler (kronolojik, detay CHANGELOG_MEMORY.md):**
PLC-HMI-20260921-09 (Aşağı talepleri) -> C0.4 takibi -> PLC-HMI-20260921-
10/11 (C5 "Başlangıç Konumuna Dön") -> UI geri bildirimi -> C5 config fix
(12) -> bugünkü MANUAL_RETURN_STOP bulgusu.

**Ayrı bulgu (beklemede):** VisionCut'tan 3 yeni mesaj (07/08/09) - ayrı
süreç mimarisi, paketlenmiş exe, build sahipliği. Kullanıcı: "sonra
ilgilenelim" - dokunulmadı.

## Siradaki Gorevler

- [ ] Kullanıcı: canlı PLC'de watch'ta `xStopActive`/`xDI_StopPB`/`xX_
      StopDone`/`xY_StopDone`/`xAxesStopped`/`xJogRequestsReleased`'ı
      izleyip hangisinin takılı olduğunu bulmalı (fiziksel Stop butonu
      latch'li mi kontrol etsin).
- [ ] PLC tarafı: `MANUAL_RETURN_STOP`'un Reset ile de çıkılabilir bir yolu
      olmalı mı kararı bekleniyor.
- [ ] "Başlangıç Konumuna Dön" gerçek PLC'ye karşı uçtan uca test edilmeli
      (bu sıkışma çözülünce).
- [ ] VisionCut 07/08/09 mesajları bekliyor.
- [ ] H4/H7: PLC C2 (alarm) kararı gelince başlanacak.
- [ ] SettingsStore `data/bufera.db` test-izolasyonu kararı bekliyor.
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 236/236 (2026-09-21).

## Son Degisiklikler

- 2026-09-21 - Busy/Aborted önceliği düzeltildi (PLC-HMI-20260921-13,
  PLC'nin bulduğu gerçek hata) - "REDDEDİLDİ" artık Busy'de gösterilmiyor.
- 2026-09-21 - MANUAL_RETURN_STOP (140) sıkışma bulgusu: CycleState
  enum eksiği düzeltildi + PLC'ye xStopActive/Reset bulgu raporu.
- 2026-09-21 - PLC-HMI-20260921-12: C5 gerçek config eksiği + "TAG EKSİK".
- 2026-09-21 - Manuel sayfa UI geri bildirimi + PLC-HMI-20260921-10/11
  ("Başlangıç Konumuna Dön") + C0.4 takibi + PLC-HMI-20260921-09.

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler izole config
  kullanmali. `data/bufera.db` PAYLAŞIMLI - testler izole ETMİYOR (bilinen).
- Vision simülatörü PLC state/sensör/motion/valf taglarına ASLA yazmaz.
- Yeni, online doğrulanmamış PLC NodeId'sini gerçek `config/opcua.json`'a
  eklemeden önce PLC tarafının online doğrulamasını bekle (C0.4/C5 dersi).
- Gerçek PLC export dosyaları proje dışında tutuluyor (`C:\Users\agedik\
  Documents\ChatGPT\Bufera Tekstil PLC\...\plc_export\`) - kod/tag sorusu
  şüpheliyse kullanıcı yolu verirse doğrudan incelenebilir (büyük XML,
  `Select-String`/chunk ile).
- VisionCut'ın gerçek mesaj kanalı `muratturan19/Brode_Vision_PLC` (dış
  repo) - bizim `visioncut_message/` klasörümüz onun el ile senkronlanan
  bir aynası, otomatik güncellenmiyor.
