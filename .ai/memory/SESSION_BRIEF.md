# SESSION_BRIEF - Son guncelleme: 2026-09-23

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**C8 "Sıfır Referansı Belirle" uygulandı, sahada test edildi, iki tur
düzeltme yapıldı (2026-09-23).** Modal servis penceresi tamamlandı ->
kullanıcı sahada denedi, buton pasif kaldı -> diyalog yanlış "koşullar
sağlanmıyor" metni gösteriyordu, düzeltildi -> ben de "PLC henüz online
doğrulamadı" diye KANITSIZ bir iddia yazmışım, diğer ajan (PLC) haklı
olarak düzeltti. Gerçek `opc.tcp://192.168.0.2:4840`'a salt-okunur
bağlanıp asyncua ile doğruladım: **`xSetZeroRequest` CANLI** (gerçek
config'e eklendi, yedekli) - **10 MC_Home RO alanı `BadNodeIdUnknown`**
(`Motion_Control` online sembol ağacında yok, Symbol Configuration'da
yayınlanmamış). PLC'den gerçek yol/yayın teyidi istendi; diyalog artık
"PLC kodu yüklenmedi" iddiası yapmayan nötr metin + eksik alan listesi
gösteriyor. Tam suite 350/350. Detay: CHANGELOG_MEMORY.md üstteki 3 giriş.

**YENİ, dokunulmamış PLC görevi:** mesaj 21 - EMG basılınca bıçak/baskı
otomatik geri çekilsin + H16 (EMG Hata) metin güncellemesi.

**Önceki (2026-09-23):** VisionCut mimari kararı (ayrı süreç) KABUL
EDİLDİ ve gerçek depoya (`Brode_Vision_PLC`) push edildi; hız parametre
sınırları gerçek mekaniğe göre revize edildi. Detay: CHANGELOG_MEMORY.md.

## Siradaki Gorevler

- [ ] PLC tarafı: 10 MC_Home RO alanının Symbol Configuration'da
      yayınlanıp yayınlanamayacağını / gerçek sembol yolunu teyit etmeli
      (`Motion_Control` düğümü şu an online sembol ağacında yok).
- [ ] **PLC-HMI-20260923-21** - EMG pnömatik geri çekme + H16 metin
      güncellemesi, henüz başlanmadı.
- [ ] VisionCut'tan 4 paketleme hatası için gerçek yama dosyası bekleniyor.
- [ ] PLC tarafı: H12-H15/H20-H22/U06 (8 aday tag) online test bekliyor.
- [ ] PLC tarafı: MANUAL_RETURN_STOP (140) Reset kararı hâlâ açık (13).
- [ ] `data/bufera.db` paylaşımlı-engine test-izolasyonu kararı bekliyor.
- [ ] Gerçek kamera devrede: `vision_simulator_enabled` kapalı tutulmalı.

## Son Build/Test

- `pytest`: 350/350 (2026-09-23).

## Son Degisiklikler

- 2026-09-23 - C8: gerçek PLC'ye salt-okunur browse (`xSetZeroRequest`
  canlı doğrulandı+config'e eklendi; 10 RO alan BadNodeIdUnknown), diyalog
  metni "PLC kodu yüklenmedi" iddiası yapmayan nötr metne çevrildi.
- 2026-09-23 - C8 diyalogu: TAG EKSİK durumunda yanlış "koşullar
  sağlanmıyor" mesajı gösteriyordu (kullanıcı sahada buldu) - düzeltildi.
- 2026-09-23 - PLC-HMI-20260923-20: C8 "Sıfır Referansı Belirle" (sade
  sürüm) - modal servis penceresi, servis state machine, yeni testler.

## Kisa Notlar

- Oturum basinda sadece bu dosya okunur; detay gerekirse `RULES.md`.
- `config/opcua.json` GERCEK PLC endpoint'i tutuyor - testler izole config
  kullanmali. Değişiklik öncesi yedekle (`config/opcua.json.bak*`,
  `.gitignore`'da). `data/bufera.db` PAYLAŞIMLI - testler izole ETMİYOR;
  test sonrası `DELETE FROM alarm_events` ile temizle.
  `engineering_settings`'e DOKUNMA.
- Vision simülatörü PLC state/sensör/motion/valf taglarına ASLA yazmaz.
- Yeni, online doğrulanmamış PLC NodeId'sini gerçek `config/opcua.json`'a
  eklemeden önce PLC tarafının online doğrulamasını bekle (C0.4/C5 dersi)
  - AMA "online doğrulanmadı" iddiasını KENDİN üretme, salt-okunur browse
  ile doğrula ya da PLC'ye sor (2026-09-23 dersi - kanıtsız "PLC yapmadı"
  çıkarımı yanlış çıktı).
- Demo modda `MachineService.start()` çağrılmadan `snapshot.stale` hep
  True kalır - smoke test yazarken `svc.snapshot.stale = False` elle set
  edilmeli.
- Gerçek PLC'ye salt-okunur `asyncua.Client` ile doğrudan bağlanıp
  browse/read yapılabilir (`opc.tcp://192.168.0.2:4840`, ns=4, security
  None/None) - 2026-09-23'te ilk kez böyle kullanıldı, çalıştı.
- **VisionCut'ın gerçek mesaj kanalı `muratturan19/Brode_Vision_PLC`**
  (dış repo, PUBLIC) - `gh` hesabımız buraya PUSH YETKİLİ. Ajanlar arası
  mesajlar BURAYA yazılır; `visioncut_message/` yalnız pasif yerel ayna.
