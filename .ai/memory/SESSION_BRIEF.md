# SESSION_BRIEF - Son guncelleme: 2026-09-23

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**VisionCut mimari kararı KABUL EDİLDİ ve gerçek depoya İLETİLDİ
(2026-09-23).** Kritik keşif: `gh` hesabımız gerçek paylaşılan depoya
(`muratturan19/Brode_Vision_PLC`) push yetkili - ve önceki `06` mesajımız
o depoya HİÇ ulaşmamıştı. Orada bizim görmediğimiz `07`/`08`/`09`
(VisionCut, 20-21 Eylül) vardı: VisionCut sahaya gitmiş, programımızı
kendi paketleyip 4 hata bulup yamalamış. Kullanıcıyla karar verdik: ayrı
süreç KABUL (`INTEGRATION.md` güncellendi), pencere başlığı düzeltildi,
tek kanal artık gerçek depo. Yanıt mesajı `10` + `KARARLAR.md` karar #1
gerçek depoya push edildi (commit `c90fbba`, doğrulandı - GitHub'da canlı).
4 hatanın kodu HENÜZ yazılmadı - gerçek yama dosyası VisionCut'tan
istendi, cevap bekleniyor. Detay: CHANGELOG_MEMORY.md üst giriş.

**YENİ, dokunulmamış PLC görevi bekliyor:** `.ai/Codex_Codesys.md`'ye
otomatik düşen mesaj 19 (iptal) + **20 (C8 "Sıfır Referansı Belirle",
GÜNCEL/yetkili)** - tek yeni tag `xSetZeroRequest`, şifreli modal + EMG
tabanlı elle konumlandırma + 3sn buton + mevcut MC_Home Done/Busy/Error
RO izleme, 5 test isteniyor. Kaynak: `.ai/HMI_C8_SADE_SURUM_20260923.md`.
Bu oturumda İNCELENMEDİ/uygulanmadı.

## Siradaki Gorevler

- [ ] **C8 Sıfır Referansı** (yeni, 20 numaralı görev) - henüz başlanmadı,
      `.ai/HMI_C8_SADE_SURUM_20260923.md`'yi oku, uygula.
- [ ] VisionCut'tan 4 hata için gerçek yama dosyası bekleniyor (08.1,
      mesaj `10` gerçek depoya push edildi, commit `c90fbba`).
- [ ] PLC tarafı: H12-H15/H20-H22/U06 (8 aday tag) online test bekliyor.
- [ ] Kullanıcı: gerçek PLC'de A01-A06/hız sınırı değişikliklerini test etmeli.
- [ ] PLC tarafı: MANUAL_RETURN_STOP (140) Reset kararı hâlâ açık (13).
- [ ] `data/bufera.db` paylaşımlı-engine test-izolasyonu kararı bekliyor.
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 306/306 (2026-09-23).

## Son Degisiklikler

- 2026-09-23 - VisionCut ayrı-süreç mimarisi kabul edildi, `INTEGRATION.md`
  güncellendi, pencere başlığı düzeltildi (`app/main.py`), yerel mesaj
  aynası gerçek depoyla senkronlandı.
- 2026-09-22 - Hız parametre sınırları gerçek mekaniğe göre revize edildi.
- 2026-09-22 - PLC-HMI-20260922-18 (C06_1 audit, A01-A06).

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler izole config
  kullanmali. `data/bufera.db` PAYLAŞIMLI - testler izole ETMİYOR; tam
  suite tek çalıştırmada birkaç satır kirlilik üretiyor (DemoSimulator'ın
  vision-heartbeat alarmı - GERÇEK PLC verisi DEĞİL). Test sonrası
  `DELETE FROM alarm_events` ile TAMAMI temizlenebilir.
  `engineering_settings`'e DOKUNMA.
- Vision simülatörü PLC state/sensör/motion/valf taglarına ASLA yazmaz.
- Yeni, online doğrulanmamış PLC NodeId'sini gerçek `config/opcua.json`'a
  eklemeden önce PLC tarafının online doğrulamasını bekle (C0.4/C5 dersi).
- Gerçek PLC export dosyaları proje dışında (`C:\Users\agedik\Documents\
  ChatGPT\Bufera Tekstil PLC\...\plc_export\`) - kullanıcı yolu verirse
  doğrudan incelenebilir (büyük XML, chunk ile).
- **VisionCut'ın gerçek mesaj kanalı `muratturan19/Brode_Vision_PLC`**
  (dış repo, PUBLIC) - `gh` hesabımız buraya PUSH YETKİLİ (collaborator,
  2026-09-23 doğrulandı). Bundan sonra ajanlar arası mesajlar BURAYA
  yazılır (karar 08.3); bizim `visioncut_message/` klasörümüz artık yalnız
  pasif yerel referans/ayna - önceki varsayım ("biz oraya yazamayız,
  kullanıcı elle senkronlamalı") YANLIŞTI, düzeltildi.
