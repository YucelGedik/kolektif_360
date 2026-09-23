# SESSION_BRIEF - Son guncelleme: 2026-09-23

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**C8 "Sıfır Referansı Belirle" TAMAMEN BİTTİ - 11/11 tag gerçek config'te,
buton gerçek makinede aktif (2026-09-23).** Süreç: modal pencere yazıldı
-> sahada buton pasif kaldı -> yanlış mesaj metni düzeltildi -> "PLC henüz
doğrulamadı" diye KANITSIZ bir iddia yazdım, PLC ajanı haklı olarak
düzeltti -> ilk salt-okunur browse'da `xSetZeroRequest` canlı çıktı ama 10
RO alan `BadNodeIdUnknown` idi -> kullanıcı yeni build indirdi, UaExpert'te
canlı gösterdi -> ikinci browse'da 10 alan da bulundu, ama GERÇEK isimler
benim tahminimden (`Motion_Control.MC_Home_X/Y.*`) FARKLIYDI: GVL
seviyesinde düz ayna değişkenler (`xX_HomeDone/Busy/Aborted/Error`,
`eX_HomeErrorID`, Y için aynısı). Hepsi doğru config'e eklendi,
`set_zero_tags_configured()` artık True, buton gerçek makinede aktif
(ekran görüntüsüyle doğrulandı). Tam suite 350/350. Detay: CHANGELOG_
MEMORY.md üstteki 4 giriş.

**Ders:** iki kez "PLC'de X eksik/doğrulanmadı" gibi bir NEDEN iddia
ettim, ikisi de ya kanıtsızdı ya da yanlış çıktı. Bundan sonra yalnız
"config'te bu anahtarlar yok" gibi GÖZLEMİ söyle, NEDEN/suçlama ekleme -
gerekiyorsa salt-okunur browse ile kanıtla.

**YENİ, dokunulmamış PLC görevi:** mesaj 21 - EMG basılınca bıçak/baskı
otomatik geri çekilsin + H16 (EMG Hata) metin güncellemesi.

**Önceki (2026-09-23):** VisionCut mimari kararı (ayrı süreç) KABUL
EDİLDİ ve gerçek depoya (`Brode_Vision_PLC`) push edildi; hız parametre
sınırları gerçek mekaniğe göre revize edildi. Detay: CHANGELOG_MEMORY.md.

## Siradaki Gorevler

- [ ] Kullanıcı: C8'i sahada fiziksel olarak dene (buton artık aktif,
      henüz gerçek bir 3sn basılı tutuş/homing denemesi yapılmadı).
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

- 2026-09-23 - C8: ikinci browse'da 10 RO alan da bulundu (GVL ayna
  değişkenleri, `Motion_Control.*` tahminim yanlıştı) - 11/11 tag gerçek
  config'te, buton gerçek makinede aktif.
- 2026-09-23 - C8: ilk browse - `xSetZeroRequest` canlı doğrulandı, 10 RO
  alan o an BadNodeIdUnknown; diyalog metni nötrleştirildi.
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
