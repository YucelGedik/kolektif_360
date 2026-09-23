# SESSION_BRIEF - Son guncelleme: 2026-09-23

> Bu dosya AI protokolunun birincil giris noktasidir.
> Her anlamli kod degisikliginden sonra guncellenir. 40 satiri gecirme.

## Aktif Durum

**Manuel/Oto mod butonu artık geçilecek moda göre etiketleniyor
(2026-09-23, kullanıcı isteği).** "MANUEL MODU ETKİNLEŞTİR" hep aynı
metni gösteriyordu, ayrı bir "OTO MODU ETKİNLEŞTİR" butonu da yoktu -
kullanıcı ana ekrandaki "oto moda geçin" uyarısıyla kafası karıştığını
söyledi. İkinci buton eklenmedi - TEK buton artık Manuel'deyken "OTO MODU
ETKİNLEŞTİR", Auto'dayken "MANUEL MODU ETKİNLEŞTİR" gösteriyor
(`manual_page.py::_on_snapshot`). 4 yeni test, gerçek render ile
doğrulandı. Tam suite 354/354.

**Önceki (2026-09-23) - C8 "Sıfır Referansı Belirle" TAMAMEN BİTTİ -
11/11 tag gerçek config'te, buton gerçek makinede aktif.** İki browse
turu sonrası (ilk turda 10 RO alan BadNodeIdUnknown'dı, kullanıcı yeni
build indirince ikinci turda hepsi bulundu - GERÇEK isimler GVL ayna
değişkenleri, `Motion_Control.*` tahminim yanlıştı) config tamamlandı.
**Ders:** iki kez "PLC'de X eksik/doğrulanmadı" gibi kanıtsız bir NEDEN
iddia ettim, ikisi de yanlış çıktı - bundan sonra yalnız gözlemi söyle,
gerekiyorsa salt-okunur browse ile kanıtla. Detay: CHANGELOG_MEMORY.md.

**YENİ, dokunulmamış PLC görevi:** mesaj 21 - EMG basılınca bıçak/baskı
otomatik geri çekilsin + H16 (EMG Hata) metin güncellemesi.

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

- `pytest`: 354/354 (2026-09-23).

## Son Degisiklikler

- 2026-09-23 - Manuel/Oto mod butonu geçilecek moda göre etiketleniyor
  (ikinci buton yok, tek buton metni değişiyor).
- 2026-09-23 - C8: iki browse turu sonrası 11/11 tag gerçek config'te,
  buton gerçek makinede aktif.
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
