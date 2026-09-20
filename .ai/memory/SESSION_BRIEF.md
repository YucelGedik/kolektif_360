# SESSION_BRIEF - Son guncelleme: 2026-09-18

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**Manuel Bıçak/Baskı Yukarı artık gerçek PLC request'lerine bağlı**
(`xBladeRetractRequest`/`xClampRetractRequest` pulse-write,
`xBladeRetractAccepted`/`xClampRetractAccepted` salt-okunur). Eski 4 buton
(Aşağı+Yukarı, hayali/hiç eşlenmemiş `cmd_blade_down/up` taglarına yazan)
kaldırıldı; artık 2 pulse buton ("...Geri Çek") + kalıcı devre dışı "Aşağı"
(PLC görevi açık, tag uydurulmadı) + Sensör/Yukarı Talebi durum kartları.
H4 (alarm mapping)/operatör mesaj akışı/H5 (Başlangıca Git) henüz YAPILMADI
- ayrı, zaten `.ai/HMI_PNEUMATIC_ALARM_CONTRACT_20260918.md` ve `.ai/HMI_
OPERATOR_RECOVERY_MESSAGES_20260918.md`'de tam sözleşmesi hazır iş.

**Ana ekrana Alarm/Uyarı/Mesaj panosu eklendi** (kullanıcı isteği, H4'ün
canlı-tag-bağımsız kısmı): 3 filtre kutusu (Hata/Uyarı/Mesaj, varsayılan
hepsi açık) + tablo, artık yalnız AKTİF (temizlenmemiş) kayıtları gösteriyor
(düzeltme: önce hepsini gösteriyordu). ALARMLAR sayfası "Güncel Alarmlar"/
"Geçmiş Alarmlar" iki sekmeye bölündü. `AlarmEvent.severity` alanı eklendi,
eski DB otomatik migrate edildi (veri kaybı yok). Canlı PLC alarm tagı YOK -
satırlar manuel/ileride doldurulacak.

**PLC-HMI-20260918-04 (H1/H2/H3/H6) tamamlandı**, kullanıcı onaylı liste
üzerinden. H4/H5/H7 PLC C2/C5/C4 sözleşmesini bekliyor - BAŞLANMADI.
- H1: "MANUEL AKTİF"->"OPERATÖR KONTROLÜ" (ÇEVRİM DURUMU'yla karışıklık).
- H2: Manuel mod butonu artık cycle_active/stale'de UI+servis seviyesinde
  fail-closed kilitli.
- H3: Start engeli nedenleri (`compute_start_inhibit_reasons`) operatöre
  gösteriliyor - xStartPermitted yeniden hesaplanmıyor, sadece açıklanıyor.
- H6: Otomatik kamerada ikinci, seçilebilir "Eğimli Çizgi" senaryosu
  (varsayılan düz çizgi korunuyor); slope/lrMaxAllowedSlope/lrY_MaxVelocity/
  Y yazılım sınırları birlikte doğrulanıyor, sabit çevrim-başlangıç referansı.

**Yan bulgu (kullanıcıya soruldu):** `data/bufera.db` (SettingsStore) testler
arasında izole değil - her `pytest` çalıştırma gerçek yerel DB'yi kirletiyor.
Şimdilik temizlendi; kalıcı çözüm `MachineService`'e `settings_db_path`
enjeksiyonu ister (H1-H6 kapsamı dışında, onay bekliyor).

## Siradaki Gorevler

- [ ] Kullanıcı gerçek PLC'de doğrulayacak: H1/H2/H3/H6 (özellikle eğimli
      kamera senaryosunu masa testinde deneyip PLC Follow davranışını
      gözlemlemek).
- [ ] H4/H5/H7: PLC C2 (alarm sözleşmesi)/C5 (Başlangıç Konumuna Git
      request/result)/C4 (timeout tag/tip) kararları gelince başlanacak.
- [ ] SettingsStore test-izolasyonu kararı (yukarıda) kullanıcıdan bekliyor.
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 178/178 (2026-09-18).

## Son Degisiklikler

- 2026-09-18 - H1/H2/H3/H6 uygulandı (detay: CHANGELOG_MEMORY.md, aynı
  tarihli ilk giriş). Ayarlar tablosuna "Sınır" sütunu, Vision Simülatör
  butonuna şifre kapısı (90327) eklendi - kullanıcı istekleri.
- 2026-09-18 - OPC UA yazımı sunucudan gerçek DataType soruyor
  (BadTypeMismatch kalıcı çözümü); `parameterWriteError` gerçek hatayı
  Settings UI'ya taşıyor.
- 2026-09-17 - Otomatik kamera modu + heartbeat-auto-start fix + gerçek
  iptal (`cancel_pending_sequence`) + cycle_active kilidi düzeltmesi.

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler izole config
  kullanmali. `data/bufera.db` PAYLAŞIMLI - testler bunu izole ETMİYOR
  (bilinen, yukarıda not edilen sorun).
- Vision simülatörü PLC state/sensör/motion/valf taglarına ASLA yazmaz.
