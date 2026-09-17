# Bufera Makine Ekranı - Degisiklik Hafizasi

Yeni girisleri en uste ekle. Eski ve uzun detaylari `CHANGELOG_ARCHIVE.md`
dosyasina tasi.

## 2026-09-16 - Parametre yazma "sessiz geri donme" hatasi (gercek PLC bug report)

Kullanici Faz 4'u gercek PLC'de test ederken: X Kesim Hızı'nı 175'ten
180'e degistirip Uygula'ya bastiginda deger sessizce 175'e geri donuyordu,
"✓ UYGULANDI" yaziyor olsa bile.

### Kok neden

`SettingsPage._apply_parameter`, `MachineService.set_parameter` cagirdiktan
HEMEN sonra yerel `_param_cache`'i (henuz PLC'ye hic ulasmamis olabilecek
degeri) okuyup "✓ UYGULANDI" gosteriyordu - kodun kendi yorumu bile bunun
"best-effort, gercek PLC'ye karsi guvenilir degil" oldugunu itiraf ediyordu.
Bagimsiz calisan 100ms okuma dongusu, yazma henuz PLC'ye ulasmadan once
gelen bir okumayi "gercek deger buymus" sanip `_param_cache`'i sessizce eski
degere donduruyordu - ve status etiketi hicbir zaman guncellenmiyordu, o
yuzden "basarili" yazisi ekranda asili kaliyordu.

### Duzeltme

- **`services/machine_service.py`**: yeni `_param_pending: dict[str,
  (value, written_at)]`. `set_parameter` artik yazdigi degeri PLC'den bir
  okumada gormeden "onaylanmis" saymiyor. `_on_raw_snapshot`'ta her
  parametre okunuşunda: pending deger varsa VE okunan deger yazilanla
  eslesirse -> `parameterWriteConfirmed` sinyali + cache guncellenir;
  eslesmiyor ama `PARAM_WRITE_CONFIRM_TIMEOUT_S` (2s) henuz gecmediyse ->
  hicbir sey yapilmaz (cache optimistik degerde kalir, UI titremez);
  timeout gectiyse -> `parameterWriteFailed` sinyali + cache PLC'nin
  gercek degerine dondurulur (artik dogru sebeple).
- **`ui/machine/settings_page.py`**: Uygula artik aninda "✓ UYGULANDI"
  yazmiyor, "Yazılıyor…" gosterip yeni `parameterWriteConfirmed`/
  `parameterWriteFailed` sinyallerini bekliyor. Basarisizlikta
  "HATA — PLC onaylamadı" gosteriliyor (ve spin zaten canli-senkron
  mekanizmasiyla PLC'nin gercek degerine geri donuyor).
- Build/Test: `pytest` **37/37** yesil - 5 yeni test
  (`tests/test_parameter_write_confirmation.py`): onay-oncesi, gec-gelen-
  stale-okuma sirasinda geri donmeme, gercek onay, timeout-sonrasi HATA,
  demo modda aninda onay.
- **Gercek PLC'de tekrar test kullanicida** - bu sefer "Yazılıyor…"dan
  sonra ✓ UYGULANDI mi yoksa HATA — PLC onaylamadı mi cikacagi, yazmanin
  PLC tarafinda gercekten kabul edilip edilmedigini dogru sekilde
  gosterecek (onceki turdaki gibi yanlis "basarili" mesaji degil).

## 2026-09-16 - Faz 2 gercek PLC'de dogrulandi + Faz 4: Ayarlar ekrani gercek parametrelerle

Kullanici Faz 2'yi gercek PLC'de test etti: "ayarlar haric her sey tamam
gibi". Ardindan Ayarlar ekranini gercek GVL parametreleriyle eslestirme
istendi (16 parametre, kullanicinin PLC GVL + Logic_Control kontrolunden
gelen kesin liste).

### Mimari analiz (once yapildi, sonra uygulandi)

`ui/machine/settings_page.py` zaten tamamen data-driven: hicbir parametre
UI'da hardcode degil, `core/parameters.py::PARAMETER_SPECS` listesinden
QGridLayout satiri olarak uretiliyor. Yani parametre listesini degistirmek
layout kodunu degistirmeyi gerektirmiyor. **Kok sorun**: `SettingsPage`
`service.snapshotUpdated`'a hic abone degildi, degerleri yalnizca
`_build_ui()`'da BIR KEZ (yerel SQLite/`SettingsStore` veya `spec.default`'tan)
okuyordu - gercek PLC'den asla, ve sonradan PLC verisi gelse bile ekran hic
guncellenmiyordu. Kullanicinin "UI default gostermeyecek" sikayeti buydu.

### Degisiklikler

- **`core/parameters.py`**: 16 parametre tamamen yeniden yazildi (asagidaki
  harita). Eski 16 kurgusal `par_*` kaldirildi. `X İvme`+`X Yavaşlama` tek
  `X Kesim Acc/Dec` oldu; `Vision Zaman Aşımı` kaldirildi (GVL'de yok);
  `Y Max Hız` -> `Y Follow Maks. Hızı` yeniden adlandirildi; `X Dönüş
  Acc/Dec`, `Y Pozisyonlama Hızı`, `Y Pozisyonlama Acc/Dec` eklendi.
  Pnomatik gecikmeler (4 adet) listeden tamamen cikarildi - GVL'de hala yok
  (Logic_Control T#500ms hard-coded), kullanicinin yeni listesinde de yoktu.
  `lrMaxAllowedSlope`/`lrStopAccDec`/`lrPositionTolerance`/
  `lrStopVelocityTolerance` bilincli olarak eklenmedi (kullanici istegi).
- **`config/opcua.json` + `opcua.example.json`**: 16 yeni `lr*`/`t*` tag,
  eski 16 `par_*` kaldirildi.
- **`services/machine_service.py`**: yeni `_param_confirmed: set[str]` -
  demo modda hepsi bastan onayli, gercek modda yalnizca `_on_raw_snapshot`'ta
  bir parametre fiilen `raw` icinde gorulunce onaylanir. Yeni
  `is_parameter_confirmed(key)`. Progress hesabindaki anahtar
  `par_x_cut_start_pos` -> `lr_x_cut_start_pos` (isim tutarliligi).
- **`ui/machine/settings_page.py`**: `snapshotUpdated`'a abone oldu. Her
  satir onaylanana kadar "Okunuyor…" gosterip kilitli kaliyor (Muhendislik
  acik olsa bile); onaylandiktan sonra her tick'te PLC'den canli senkron
  oluyor (`spin.hasFocus()` iken dokunmuyor - kullaniciyla yarismiyor).
- Build/Test: `py_compile` temiz, `pytest` **32/32** yesil (6 yeni test:
  parametre listesi tam/eksiksiz kontrolu x4, confirmed-tracking x2). Ayrica
  `services/demo_simulator.py` icindeki tum eski `par_*` anahtar
  referanslari (`_apply_manual_controls`, `CUTTING`, `RETURN_AXES`,
  `_return_axes`) yeni isimlere tasindi - degistirilmeseydi demo cevrimi
  `KeyError` ile cokerdi (testler bunu yakaladi).
- **Gercek PLC read/write testi kullanicida** (AI'nin PLC agina erisimi yok).

## 2026-09-16 - Faz 1 duzeltmeleri + Faz 2: yazma tarafi gercek PLC'ye baglandi

Kullanici gercek PLC'ye bagli (`opc.tcp://192.168.0.2:4840`, UaExpert ile
dogrulanmis). Bu oturumda uc ayri asama var: (1) Faz 1'e 5 duzeltme, (2)
canli config dosyasindaki iki ayri kopyalama-eksikligi hatasi, (3) Faz 2
(write binding).

### Faz 1 duzeltmeleri (kullanici onayi ile)

- **`xStartPermitted` artik dogrudan PLC'den okunuyor**, HMI kendi
  formulunu (MachineReady AND NOT xManualMode AND NOT xCycleActive AND
  xX_AtStart AND xY_AtCenter) tekrarlamiyor. `x_at_start`/`y_at_center`
  diagnostic olarak eklendi (`core/models.py`, `services/machine_service.py`).
- **`xCycleActive` da dogrudan okunuyor**, eMachineState'ten turetilmiyor.
- **`services/demo_simulator.py` gercek PLC akisiyla birebir**: MANUAL
  sadece `manual_mode=True` iken gosteriliyor (auto-mod dinlenme durumu
  WAIT_FOR_MATERIAL); normal STOP artik RECOVERY'den GECMIYOR (STOPPING ->
  BLADE_UP direkt); RECOVERY sadece FAULT+Reset sonrasi giriliyor. Eski 5
  parcali `_advance_recovery` yardimcisi tamamen kaldirildi (artik gereksiz).
- Kesim ilerlemesi formulu (ActualX-CutStart)/(CutEndX-CutStart) demo'nun
  kendi CUTTING hesabina da tasindi (tutarlilik).
- **Guvenlik**: 13 kurgusal `cmd_*` yazma tag'i `config/opcua.example.json`'dan
  kaldirildi - Faz 2 gelene kadar gercek PLC'de kullanilirlarsa sessizce
  no-op olup loglanacak sekilde.

### Canli config dosyasi hatalari (kullanicinin kendi PLC testi sirasinda bulundu)

1. Ayarlar ekranina girilen endpoint'te port eksikti (`opc.tcp://192.168.0.2`
   -> `:4840` olmadan `asyncio.create_connection` aninda OSError veriyordu,
   sonsuz reconnect donguyor). Deneyerek dogrulandi, port eklendi.
2. `config/opcua.json` (aktif/canli dosya) hicbir zaman `opcua.example.json`
   sablonundan kopyalanmamisti - sadece eski tek bir orphan tag
   (`ipc_y_pos`) vardi. PLC baglaniyordu ama okunan tek tag oydu, gerisi hep
   varsayilan degerde donuyordu ("veri gelmiyor" hissi). Sablon nodes'u
   endpoint korunarak aktif dosyaya islendi.

### Faz 2: yazma tarafi (kullanici onayi ile, gercek GVL tag'leriyle)

- **`config/opcua.json` + `config/opcua.example.json`**: `cmd_start` ->
  `GVL.Start`, `cmd_stop` -> `GVL.Stop`, `cmd_reset` -> `GVL.Reset`,
  `jog_x_plus_request`/`jog_x_minus_request`/`jog_y_plus_request`/
  `jog_y_minus_request` -> `GVL.xX/Y_Jog*Request`. `manual_mode` zaten
  vardi (`xManualMode`), hem okuma hem yazma icin ayni key kullaniliyor.
- **`plc/opcua_client.py`**: `request_pulse` artik ayni komut icin ikinci
  pulse'u SENKRON olarak (schedule etmeden once) engelliyor
  (`_pulses_in_flight` set'i). **Gercek bir hata yakalandi+duzeltildi**: ilk
  yazimda guard `_pulse()` coroutine'i icinde (async) isaretleniyordu, iki
  `request_pulse()` cagrisi arka arkaya (await olmadan) geldiginde ikinci
  cagri ilkinin daha baslamadigini goruyor, guard calismiyordu. Test
  (`tests/test_opcua_pulse_guard.py`) bunu yakaladi.
- **`services/machine_service.py`**: `request_start/stop` degismedi (zaten
  dogru pulse deseni), sadece config'teki NodeId'ler gercek oldu.
  `set_auto_mode` kaldirilip yerine `set_manual_mode(manual: bool)` geldi -
  duz yazma (pulse degil), `xManualMode`'a. Jog metodlari yeni
  `jog_x_plus_request` vb. tag'lere yaziyor. Yeni `release_all_jog()`:
  `_manual_allowed()` kontrolune tabi DEGIL (birakma/guvenlik her zaman
  calismali), 4 jog request tag'ini FALSE'a cekiyor.
- **`ui/machine/manual_page.py`**: basliga "MANUEL MODU ETKİNLEŞTİR"
  checkable butonu eklendi (`xManualMode`'a yazar, PLC onayini
  `_on_snapshot`'ta `blockSignals` ile senkron gosterir - optimistic degil).
  `hideEvent` (sayfadan cikis) ve `QApplication.applicationStateChanged`
  (pencere odak kaybi) her ikisi de `release_all_jog()` cagiriyor.
- **Dokunulmayanlar (kasitli)**: `y_center`/`set_blade`/`set_clamp` hala eski
  kurgusal taglara yaziyor (config'te yok, no-op) - Faz 3'un isi. Ayarlar,
  Vision Simulator'a hic dokunulmadi.
- Build/Test: `py_compile` temiz, `pytest` **26/26** yesil (6 yeni test:
  pulse-guard x3, set_manual_mode/release_all_jog demo davranisi x2,
  OpcUaConfig izolasyon testi x1). **Gercek PLC'ye karsi buton testi
  (Start/Stop/Reset pulse, Jog press/release, Manual/Auto write, write
  failure) AI'nin erisemedigi kullanicinin PLC agi uzerinde yapilmali.**

## 2026-09-16 - Faz 1: Ana Ekran PLC->HMI read binding (onayli)

Kaynak: `docs/BUFERA_HMI_PLC_ENTEGRASYON_GOREV_PLANI.md` + kullanicinin
2026-09-16 tarihli duzeltmeleriyle onaylanan tag/formul/enum spesifikasyonu.
Sadece okuma yonu; START/STOP/RESET/JOG/manuel yazma islemlerine dokunulmadi.

- **`core/cycle_state.py`** (tam yeniden yazim): `CycleState` enum'u artik
  gercek PLC `eMachineState` degerleri (INIT=0, MANUAL=10, ...,
  CYCLE_COMPLETE=120, STOPPING=500, RECOVERY=510, FAULT=900). Eski enum
  numaralari (IDLE=10, CLAMP_DOWN=50, BLADE_UP=100 ...) gercek degerlerle
  cakisiyordu, tamamen degistirildi. `AUTO_CYCLE_ACTIVE_STATES`/
  `RECOVERY_STATES` yeni uyelere gore guncellendi.
- **`services/demo_simulator.py`**: tum `CycleState.*` referanslari yeni
  enum'a tasindi; ALIGN_Y ve WAIT_BLADE_REQUEST icin yeni kisa fazlar
  eklendi (gercek PLC'de var, eskiden demo'da yoktu); 5 parcali eski
  recovery zinciri (RECOVERY_BLADE_UP/RETURN_X/CENTER_Y/CLAMP_UP) tek
  `RECOVERY(510)` kodu altinda internal `_recovery_step` ile birlestirildi
  (gercek PLC de tek kod donuyor). Davranis/zamanlama korunuyor.
- **`core/models.py`**: kullanilmayan `estop_ok`/`safety_ok` kaldirildi
  (hicbir UI onlari okumuyordu); `cut_active`, `emergency_active`,
  `trajectory_fault`, `feed_complete` eklendi (yeni sozlesmenin tag'leri,
  henuz hicbir widget'ta gosterilmiyor - ileri faz icin hazir).
- **`services/machine_service.py::_on_raw_snapshot`**: `x_servo_ready`/
  `y_servo_ready` artik `PowerStatus AND NOT PowerError` turetmesi;
  `clamp_up`/`blade_up` artik `NOT clamp_down`/`NOT blade_down` turetmesi
  (PLC'de ayri sensor tagi yok); `auto_mode = NOT manual_mode`;
  `cycle_active = eMachineState in AUTO_CYCLE_ACTIVE_STATES`;
  `start_permitted = machine_ready AND NOT cycle_active AND NOT manual_mode`
  (plan SS4 formulu); kesim ilerlemesi artik PLC'den okunmuyor, kullanicinin
  onayladigi duzeltilmis formulle turetiliyor:
  `%clamp(100*(ActualX_mm-lrX_CutStartPos)/(CutEndX_mm-lrX_CutStartPos), 0, 100)`.
- **`ui/machine/machine_page.py`**: Vision Hazir kosulu
  `VisionReady AND xVisionHeartbeatOK AND NOT VisionFault` oldu; heartbeat
  kaybinda ayri "VISION: YANIT YOK" durumu eklendi (sadece bu bir mantik
  degisikligi, tasarima/layout'a dokunulmadi).
- **`config/opcua.example.json`**: kurgusal `HMI_*` okuma tag'leri (17 adet
  + estop_ok/safety_ok) kaldirildi; onaylanan 23 gercek tag eklendi (19
  Ana Ekran SS3 + VisionReady/VisionFault SS2 chip icin + lrX_CutStartPos/
  CutEndX_mm progress formulu icin). Yazma tarafi (`cmd_*`/`par_*`) hic
  degistirilmedi - Faz 2-4'te ele alinacak. `par_x_cut_start_pos` NodeId'i
  gercek `lrX_CutStartPos`'a duzeltildi (eskiden kurgusal `PAR_X_CutStartPos`).
- **Yeni testler**: `tests/test_machine_service_bindings.py` (6 test - servo
  ready turetmesi, clamp/blade up turetmesi, auto_mode turetmesi,
  cycle_active/start_permitted turetmesi, progress formulu + clamp);
  `tests/test_demo_simulator_cycle.py` (3 test - tam oto cevrim MANUAL'a
  geri donuyor ve tum yeni state'leri ziyaret ediyor, stop->STOPPING->
  RECOVERY->MANUAL akisi, AUTO_CYCLE_ACTIVE_STATES enum gecerliligi).
  `tests/test_tag_map.py`'deki eski `ipc_y_pos` testi `y_actual_pos`'a
  guncellendi (orphan tag kaldirildigi icin).
- **Bilinen/kalan mock noktalari**: `feed_forward_input`/`feed_reverse_input`
  (yeni sozlesmede karsiligi yok, hep False kalacak), `x_fault_code`/
  `y_fault_code` (yeni sozlesmede fault-code tagi yok), `alarm_active/code/
  count` (Faz 5'te edge-based alarm engine gelene kadar sadece demo modda
  dolu), `vision_target_x/y`/`confidence`/`slope` (Faz 6 Vision Simulator
  eklenene kadar bos), Ayarlar ekranindaki tum parametreler haricinde
  `par_x_cut_start_pos` (Faz 4'e kadar diger par_* tag'leri hala kurgusal
  isimlerle).
- Build/Test: `python -m py_compile` (5 dosya) + `pytest` 17/17 yesil
  (2026-09-16).

## 2026-09-12 (devam - UI ince ayar)

### Kullanici geri bildirimiyle bulunan 3 gorsel kusur duzeltildi

- Degisen dosyalar: `ui/machine/manual_page.py`, `ui/machine/widgets.py`,
  `ui/machine/machine_page.py`.
- Kaynak: kullanici uygulamayi kendi terminalinden calistirip ekran
  goruntusu + geri bildirim gonderdi (bu ortamdaki AI'nin kendi baslatma
  denemesi GUI penceresi acmadan takili kaldi, CPU=0 - detay `RULES.md`
  Faz 7 notlarinda; muhtemelen bu araç oturumunun goruntu baglami farkli).
- Duzeltmeler:
  1. Manuel/Servis ekraninda X ekseni karti Y ekseni kartiyla ayni satir
     sayisina sahip degildi (Y'de "MERKEZE GİT / Y=0" butonu var, X'te
     karsiligi yok -> boyle bir PLC/servis komutu da yok, uydurulmadi).
     Duzeltme: X kartina ayni yukseklikte (`MIN_TOUCH_HEIGHT`) bos bir
     spacer eklendi, ACTUAL POSITION/SERVO kutulari artik iki kolonda ayni
     hizada.
  2. Operator ekraninda ust durum cubugu (`StatusChip` + `statusBar`
     `QFrame`'i) dikey `QSizePolicy` "Fixed" degildi -> pencere/oturum
     buyuyunce kalan bosluk bu ogelere gidip devasa/orantisiz gorunuyordu.
     Duzeltme: ikisi de `QSizePolicy.Policy.Fixed` (dikey) yapildi.
  3. Operator ekraninda alt navigasyon sekmeleri (MANUEL/AYARLAR/ALARMLAR/
     KAMERA EKRANI) sayfanin ortasinda kaliyordu, altinda bosluk vardi.
     Duzeltme: `root.addStretch(1)` sekmelerden ONCE eklenerek CNC
     kontrolculerindeki gibi sekmeler ekranin en altina sabitlendi.
- Build/Test: `python -m py_compile` (3 dosya) + `pytest` 8/8 gecti.
  Gorsel dogrulama kullanicinin kendi calistirmasina birakildi.

## 2026-09-12

### AI hafiza sistemi projeye uyarlandi

- Eklenenler: `CLAUDE.md`, `.ai/` (INDEX, RULES, memory/*, skills/design/*, hooks/*)
- Kaynak: `D:\work\GitProjects\MilGor_Project\ai-starter-kit` sablonlari,
  Bufera projesinin gercek durumuyla dolduruldu (TODO birakilmadi).
- Build/Test: etkilenmedi (sadece dokumantasyon/hafiza dosyalari).

### Ilk proje iskeleti + iki gercek hata duzeltmesi

- Eklenenler: `core/`, `plc/`, `services/`, `persistence/`, `ui/machine/`,
  `app/main.py`, `tests/`, `config/opcua*.json`, `README.md`, `INTEGRATION.md`.
- Duzeltilen hatalar (gercek calistirma + ekran goruntusu ile bulundu):
  1. `manual_page.py`/`settings_page.py`/`alarm_page.py` "Ana Ekran" geri
     butonu `"main"` anahtari yayiyordu, `app/main.py` sozlugu
     `"machine_main"` bekliyordu -> KeyError, operator sayfada kilitleniyordu.
     Duzeltme: uc sayfa da `"machine_main"` yaymaya cekildi.
  2. `app/main.py::main()` icinde `service.start()`, `MainWindow` (ve onun
     sinyal aboneleri) olusturulmadan ONCE cagiriliyordu -> ilk Demo mod
     bildirimi kimse dinlemeden kayboluyordu, status bar "PLC: --" gosteriyordu.
     Duzeltme: `service.start()` cagrisi `MainWindow` olusturulup `show()`
     yapildiktan sonraya alindi.
- Build/Test: `pytest` 8/8 gecti. `python -m app.main` gercekten calistirilip
  PowerShell + UI Automation ile 4 ekranin ekran goruntusu alindi (Operator,
  Manuel, Ayarlar, Alarmlar) ve dogrulandi.
