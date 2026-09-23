# SESSION_BRIEF - Son guncelleme: 2026-09-23

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**C8 "Sıfır Referansı Belirle" (PLC-HMI-20260923-20, sade sürüm) TAMAMLANDI.**
Mevcut fiziksel X/Y konumunu 0 yapan, şifreli, uygulama-genelinde MODAL
servis penceresi: Ayarlar → "SIFIR REFERANSI BELİRLE ⚙" → şifre → talimat
+ 3sn `HoldButton` → tek RW `xSetZeroRequest` (LEVEL, C5'teki "cleared"
deseniyle) → mevcut `MC_Home_X`/`MC_Home_Y` FB'lerinin 10 RO üyesi izlenir.
Bağlantı kaybı/15sn zaman aşımı/tek-eksen-başarı-sayılmaz hepsi kapsandı.
10 aday tag (`config/opcua.example.json`, NodeId yolu TAHMİN - PLC'den
teyit istendi). Tam suite 346/346, gerçek render + demo 50ms tick
döngüsüyle uçtan uca doğrulandı. Detay: CHANGELOG_MEMORY.md üst giriş.

**YENİ, dokunulmamış PLC görevi:** mesaj 21 - EMG basılınca bıçak/baskı
otomatik geri çekilsin + H16 (EMG Hata) metin güncellemesi. Alındı
bildirimi yazıldı, henüz uygulanmadı.

**Önceki (2026-09-23) - VisionCut mimari kararı KABUL EDİLDİ ve gerçek
depoya İLETİLDİ:** ayrı süreç (`INTEGRATION.md` güncellendi), pencere
başlığı düzeltildi, tek kanal artık `muratturan19/Brode_Vision_PLC`
(`gh` push yetkili). 4 paketleme hatası için VisionCut'tan gerçek yama
dosyası bekleniyor. Detay: CHANGELOG_MEMORY.md.

## Siradaki Gorevler

- [ ] **PLC-HMI-20260923-21** (yeni) - EMG pnömatik geri çekme + H16 metin
      güncellemesi, henüz başlanmadı.
- [ ] PLC tarafı: C8'in 11 aday tag'inin (`cmd_set_zero_request` + 10 RO
      Motion_Control.MC_Home_X/Y üyesi) gerçek NodeId yolunu teyit etmeli
      (iç FB üyesi sembol yayını dahi kesin değil) - sonra gerçek config'e
      eklenecek.
- [ ] VisionCut'tan 4 hata için gerçek yama dosyası bekleniyor (08.1).
- [ ] PLC tarafı: H12-H15/H20-H22/U06 (8 aday tag) online test bekliyor.
- [ ] Kullanıcı: gerçek PLC'de C8, A01-A06, hız sınırı değişikliklerini
      test etmeli (C8 sahada hiç denenmedi - PLC'nin kendi notu).
- [ ] PLC tarafı: MANUAL_RETURN_STOP (140) Reset kararı hâlâ açık (13).
- [ ] `data/bufera.db` paylaşımlı-engine test-izolasyonu kararı bekliyor.
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 346/346 (2026-09-23).

## Son Degisiklikler

- 2026-09-23 - PLC-HMI-20260923-20: C8 "Sıfır Referansı Belirle" (sade
  sürüm) - modal servis penceresi, `set_zero_dialog.py` (yeni), servis
  state machine, 40 yeni test.
- 2026-09-23 - VisionCut ayrı-süreç mimarisi kabul edildi + gerçek mesaj
  kanalına (`Brode_Vision_PLC`) push edildi.
- 2026-09-22 - Hız parametre sınırları gerçek mekaniğe göre revize edildi.

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
- Demo modda `MachineService.start()` çağrılmadan `snapshot.stale` hep
  True kalır (yalnız `start()` içinde False yapılır) - smoke test/manuel
  script yazarken `svc.snapshot.stale = False` elle set edilmeli, yoksa
  tüm izin kapıları (`_pneumatic_common_allowed` vb.) sessizce False döner.
- Gerçek PLC export dosyaları proje dışında (`C:\Users\agedik\Documents\
  ChatGPT\Bufera Tekstil PLC\...\plc_export\`) - kullanıcı yolu verirse
  doğrudan incelenebilir (büyük XML, chunk ile).
- **VisionCut'ın gerçek mesaj kanalı `muratturan19/Brode_Vision_PLC`**
  (dış repo, PUBLIC) - `gh` hesabımız buraya PUSH YETKİLİ (collaborator,
  2026-09-23 doğrulandı). Ajanlar arası mesajlar BURAYA yazılır (karar
  08.3); bizim `visioncut_message/` klasörümüz artık yalnız pasif yerel
  referans/ayna.
