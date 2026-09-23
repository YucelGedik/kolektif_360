# Bufera Makine Ekranı - Proje Kurallari

## Mimari Kurallar

### Klasor Yapisi

```text
core/         CycleState enum, MachineSnapshot, parametre tanimlari - Qt/asyncua'dan bagimsiz
plc/          OpcUaConfig (pydantic), tag_map (config -> NodeId), opcua_client (asyncua, QThread)
services/     machine_service.py (TEK merkezi servis) + demo_simulator.py (PLC yokken)
persistence/  SQLite: alarm gecmisi (alarms.py), muhendislik parametre override (settings_store.py)
ui/machine/   4 ekran: machine_page (operator), manual_page, settings_page, alarm_page
              + theme.py (VisionCut renk/font tokenlari), widgets.py (Card/Readout/StatusChip/HoldButton)
app/          main.py - bagimsiz gelistirme/demo kabugu (VisionCut'in kendisi DEGIL)
config/       opcua.example.json (referans, git'te) / opcua.json (gercek, gitignore'lu)
persistence data/  bufera.db (SQLite, gitignore'lu)
tests/        pytest: tag_map ve cycle_state sanity testleri
docs/         orijinal 32 bolumluk entegrasyon brifi
```

### Kod Organizasyonu

- UI (`ui/machine/`) hicbir zaman dogrudan `plc.opcua_client` kullanmaz;
  her zaman `services.machine_service.MachineService` uzerinden gecer.
- OPC UA NodeId'ler asla hard-code edilmez; `config/opcua.json` -> `plc/tag_map.py`
  uzerinden cozulur (brif SS10, SS26).
- CycleState numeric kodlari ve Turkce karsiliklari yalnizca
  `core/cycle_state.py` icinde tanimlanir; UI hicbir yerde ham int gostermez.
- Muhendislik parametre limitleri yalnizca `core/parameters.py` icindeki
  `PARAMETER_SPECS` listesinde tanimlanir.
- Yeni abstraction sadece gercek tekrar veya karmasayi azaltinca eklenecek.
- Projeye ozel kararlar `.ai/memory/DECISIONS.md` icine yazilacak.

### Stil ve Tutarlilik

- Mevcut kod stiline uy (docstring'ler kisa, "neden" aciklayan yorumlar,
  cok satirli yorum bloklari yok).
- Kullanici degisikliklerini geri alma.
- Buyuk refactor icin once onay al.
- UI metinleri Turkce, kod/degisken adlari Ingilizce (brif SS9, SS14 ile uyumlu).

## Build ve Test Kurali

- Build: `python -m venv .venv` + `.venv\Scripts\pip install -r requirements.txt`
- Run: `.venv\Scripts\python.exe -m app.main` (Demo modda calisir)
- Test: `.venv\Scripts\python.exe -m pytest`
- Son build/test: 2026-09-21 - `pytest` 235/235 gecti (C5 "Başlangıç
  Konumuna Dön" tek buton + C0.4 takibi + PLC-HMI-20260921-09 dahil); demo
  modda widget smoke testiyle dogrulandi (bkz. CHANGELOG_MEMORY.md).

Her anlamli degisiklikten sonra `pytest` calistir. UI degisikligi yapildiysa
mumkunse `python -m app.main` ile gercekten ac ve gez (bkz. DESIGN.tr.md).

## Gelistirme Kurallari

### Yeni Ozellik Eklerken

1. Mevcut benzer ornegi bul (orn. yeni bir manuel komut icin `manual_page.py`
   + `MachineService.set_blade/set_clamp` orneklerine bak).
2. En kucuk guvenli degisikligi yap.
3. `pytest` calistir; UI ise gercekten calistirip dogrula.
4. `SESSION_BRIEF.md`, `RULES.md`, `CHANGELOG_MEMORY.md` guncelle.

### Bug Fix Yaparken

1. Semptomu ve muhtemel kok nedeni ayir.
2. Ilgili dosyanin sadece gereken bolumunu oku.
3. Fix'i dar kapsamli tut.
4. `pytest` ve/veya gercek calistirma ile dogrula.

### Koklu Degisiklikler - Once Onay Al

- Mimari katman degisimi (`core/plc/services/ui` sinirlarinin bozulmasi)
- Yeni harici kutuphane (OpenCV/NumPy bilerek disarida birakildi, brif SS2
  vs bizim kapsamimiz farkli)
- OPC UA tag sozlesmesinin degistirilmesi (`config/opcua.example.json`)
- Public API veya dosya formati degisimi
- Buyuk dosya tasima/yeniden adlandirma

## Aktif Yol Haritasi

Brif SS25'teki Faz 1-6 bu projede tek oturumda kapsanmis durumda; asagidaki
liste kalan/ince ayar isleridir.

### Aktif Faz

**Faz 8 - HMI/PLC entegrasyonu (docs/BUFERA_HMI_PLC_ENTEGRASYON_GOREV_PLANI.md)**

Faz 1 (Ana Ekran PLC->HMI read binding) tamamlandi ve onaylandi (2026-09-16).
Detay: `.ai/memory/CHANGELOG_MEMORY.md`. Sirada plan dosyasinin SS12
"Uygulama sirasi" adimlari:

- [x] Faz 2 - START/STOP/RESET pulse write + Jog X/Y press-hold + Manual/Auto
      write (2026-09-16, kullanici gercek PLC'de dogruladi: "ayarlar haric
      her sey tamam"). Detay `.ai/memory/CHANGELOG_MEMORY.md`.
- [x] Faz 4 - Ayarlar ekrani gercek `lr*`/`t*` GVL parametreleriyle
      eslestirildi (2026-09-16, kod onaylandi; gercek PLC read/write testi
      kullanicida). Pnomatik gecikmeler + Vision Zaman Asimi listeden
      cikarildi (GVL'de karsiligi yok). Detay `CHANGELOG_MEMORY.md`.
- [ ] Faz 3: Blade/Clamp manuel *Request tag'leri + Y merkez (plan SS6:
      `xManualBladeDownRequest`/`xManualClampDownRequest`/`xY_CenterRequest`
      PLC'de acilana kadar ilgili butonlar pasif kalacak).
- [ ] Faz 5: Alarm engine'i edge-based yap (plan SS8 - su an AlarmCount
      PLC tagi yok, aktif alarm kosullarindan turetilmeli).
- [ ] Faz 6: Vision Simulator ekrani ekle (plan SS9).
- [ ] Gercek PLC ile `BadTypeMismatch` gorulursen `plc/opcua_client.py`
      icinde ilgili tag icin acik `ua.VariantType` eklenecek.
- [ ] Diger ekranlarda (Ayarlar, Alarmlar) benzer hizalama/sabit-yukseklik
      kontrolu yap (Manuel/Servis ve Operator'de bulunan sorunlar duzeltildi,
      ayni desen digerlerinde de kontrol edilmeli).

### Bekleyen Isler

- [ ] VisionCut'i yapan sirkete teslim oncesi `INTEGRATION.md` son kontrolu.
- [ ] Gercek PLC/OPC UA sunucusu erisilebilir oldugunda ucdan uca test.
- [ ] VisionCut mimari karari (ayri surec) kabul edildi (2026-09-23) - kod
      uygulamasi (`app/main.py`, `plc/tag_map.py`, `persistence/db.py`)
      VisionCut'in gercek yama dosyasini bekliyor (detay CHANGELOG_MEMORY.md).
- [ ] **PLC-HMI-20260923-21** (yeni, baslanmadi) - EMG basilinca bicak/
      baski otomatik geri cekilsin + H16 (EMG Hata) metin guncellemesi.

### Tamamlananlar

- [x] AI hafiza sistemi kuruldu (`ai-starter-kit`'ten uyarlandi, 2026-09-12).
- [x] Proje iskeleti: `core/plc/services/persistence/ui/app` katmanlari.
- [x] Demo modu: PLC olmadan calisan tam cevrim simulasyonu (Start/Stop/
      Reset/Recovery/Alarm).
- [x] 4 ekran (Operator, Manuel/Servis, Ayarlar/Muhendislik, Alarmlar)
      gercekten calistirilip ekran goruntusuyle dogrulandi.
- [x] `pytest` (tag_map, cycle_state) 8/8 yesil.
- [x] Git deposu baslatildi, ilk commit atildi (lokal).
- [x] GitHub'a (`YucelGedik/kolektif_360`, `master` branch) push edildi.
- [x] `.ai/hooks/session_brief_inject.ps1` hook'unun oturum basinda otomatik
      calistigi dogrulandi (2026-09-12, ayni oturumda SESSION_BRIEF context'e
      enjekte edildigi gozlemlendi).
- [x] Kullanici gercek UI uzerinde bulunan 3 gorsel kusuru bildirdi, ucu de
      duzeltildi (2026-09-12): Manuel/Servis X/Y ekseni kartlari hizasizligi,
      Operator ekrani ust durum cubugu (StatusChip) pencere buyuyunce asiri
      dikey gerilmesi, alt navigasyon sekmelerinin ekranin altina sabitlenmesi
      (CNC tarzi sayfa gecisi).
- [x] Faz 1 - Ana Ekran PLC->HMI read binding (2026-09-16, onayli): gercek
      `eMachineState`/`ActualX_mm`/`xX_PowerStatus` vb. 23 tag `config/
      opcua.example.json`'a islendi; `core/cycle_state.py` plan SS5'teki
      kesin degerlerle yeniden yazildi; `core/models.py`+
      `services/machine_service.py`'de servo-ready/cycle_active/
      start_permitted/kesim ilerlemesi turetmeleri eklendi; demo simulasyonu
      yeni state numaralarina tasindi, davranisi bozulmadi (17/17 pytest).

### 2026-09-17 — Kullanıcı önceliği: geçici Vision simülatörü (tamamlandı)
- [x] Faz 0: sözleşme/kaynak farkları raporlandı (bkz. CHANGELOG_MEMORY.md
      ve .ai/Codex_Codesys.md yanıtı - eksik NodeId'ler GVL_LAST_SHARED_
      REFERENCE.st ve 05_VISION_PLC_CONTRACT_SUMMARY.md ile doğrulandı).
- [x] Faz 1: `vision_simulator_enabled` (varsayılan false, config bayrağı),
      giriş noktası yalnız Mühendislik Erişimi açıkken görünür/aktif, her
      bağlantı durumu değişiminde zorla disarm, generation sayacıyla eski
      kuyruk/sonuç yok sayılır.
- [x] Faz 2: `OpcUaWorker.request_write_sequence` gerçek sıralı (await'li)
      yazma; `VisionSimulatorService.send_packet` TargetX/TargetY/Ready/
      LineValid/Fault/Confidence sonra Sequence sırasıyla, tek seferde bir
      paket; heartbeat periyodu `t_vision_heartbeat_timeout`/3'ten türetilir.
- [x] Faz 3: `ui/machine/vision_simulator_page.py` - modeless popup
      (`show()`, `exec()` degil - ana ekran paralel kullanılabilir, kullanıcı
      isteği); varsayılanlar FALSE, açılışta hiçbir yazı yok, ZDownRequest
      ayrı onay istiyor.
- [x] Faz 4: sayfa kapanışı/yetki kaybı/bağlantı kaybı/app kapanışında
      disarm; çevrim aktifken disarm izin alanlarını geri ÇEKMEZ (uyarır).
- [x] Faz 5: `tests/test_vision_simulator.py` (27) + `tests/
      test_opcua_sequential_write.py` (4) - hepsi fake/mock worker ile,
      gerçek PLC'ye yazma yok. Tam suite 79/79 yeşil.
Bu alt fazlar GEÇİCİ mühendislik aracının ayrıntısıdır; yukarıdaki kalıcı
"Faz 6: Vision Simulator ekrani" (plan SS9) ile karıştırılmasın - o ayrı,
kalıcı bir operatör özelliğidir ve henüz başlanmadı.

### 2026-09-17 — PLC-HMI-20260917-03: tam otomatik masa testi (tamamlandı)
- [x] Faz A: UInt32 tip hatası (vision_sequence/vision_heartbeat) düzeltildi
      - `ua.Variant(int(value), ua.VariantType.UInt32)`, gerçek OPC UA hata
        metni artık UI'ya taşınıyor.
- [x] Faz B/C: `VisionSimulatorService.start_auto_camera()` +
      `_on_auto_camera_tick()` - PLC state/actual X/xTrajectoryValid-Fault'a
      göre TargetX/TargetY/CutPermit/ZDownRequest kendiliğinden üretiliyor
      (Faz C tablosu tam uygulandı); manuel kontroller otomatik modda pasif.
- [x] Faz D: disarm/reconnect artık bekleyen paketi GERÇEKTEN iptal ediyor
      (`OpcUaWorker.cancel_pending_sequence`, sadece sinyal sonucu değil);
      `y_actual_vel` eklendi (PLC notu: lrY_ActualVelocity zaten vardı).
- [x] Faz E: `tests/test_auto_camera.py` (20) + `tests/
      test_opcua_cancel_pending.py` (3). Tam suite 111/111. Gerçek PLC'ye
      kendi kendine yazılmadı.
- [x] `.ai/Codex_Codesys.md`'ye HMI->PLC yanıtı + kullanıcı rehberi eklendi.

### 2026-09-18 — PLC-HMI-20260918-04: H1/H2/H3/H6 (kullanıcı onaylı, tamamlandı)
Kaynak: `.ai/HMI_TEST_FINDINGS_TASKS_20260918.md`. H4/H5/H7 PLC C2/C5/C4
sözleşmesini bekliyor - BAŞLANMADI (kullanıcı onayı: "H4 5 7 PLC tarafını
bekleyecek").
- [x] H1: "MANUEL AKTİF" -> "OPERATÖR KONTROLÜ"; feed izni tek başına
      `feed_manual_allowed`'a güveniyor. ÇEVRİM DURUMU zaten eMachineState'ten
      geliyordu (doğrulandı).
- [x] H2: Manuel mod butonu + `MachineService.set_manual_mode` -
      cycle_active/stale/disconnected'da fail-closed, UI+servis seviyesi.
- [x] H3: `compute_start_inhibit_reasons` - StartPermitted=FALSE nedenini
      mevcut tag'lerden açıklar, xStartPermitted'i yeniden hesaplamaz;
      "Stop basılı" YOK (gerçek tag yok, tahmin edilmedi).
- [x] H6: Otomatik kamera "tilted" senaryosu - sabit referans, üç katmanlı
      ön-kontrol (lrMaxAllowedSlope/lrY_MaxVelocity/Y yazılım sınırları),
      `send_packet`'te senaryo-bağımsız gerçek zamanlı Y-sınır reddi.
- [x] Testler: `test_mode_change_guard.py` (8), `test_start_inhibit_
      reasons.py` (12), `test_tilted_camera_scenario.py` (15). Tam suite
      160/160.
- [ ] Yan bulgu (kullanıcıya soruldu, henüz kararlaştırılmadı): paylaşımlı
      `data/bufera.db` SettingsStore testler arasında izole değil - test
      çalıştırma her seferinde gerçek DB'yi kirletiyor. Kalıcı düzeltme
      `MachineService`'e `settings_db_path` enjeksiyonu gerektirir.

### 2026-09-18 — Ana ekran Alarm/Uyarı/Mesaj panosu (tamamlandı)
Kullanıcı isteği; H4'ün "ekran/tarihçe modeli hazırlanabilir, canlı alarm
tagı tahmin edilmez" kapsamına giriyor.
- [x] `AlarmEvent.severity` (ALARM/UYARI/MESAJ) + `log_event()`; eski
      `data/bufera.db` şeması otomatik migrate edildi (veri kaybı yok).
- [x] `machine_page.py`: 3 filtre kutusu (varsayılan hepsi açık) + tablo.
      `alarm_page.py`: "Tür" sütunu eklendi.
- [x] `tests/test_alarm_severity.py` (8, izole tmp_path DB). Tam suite
      168/168. Canlı PLC alarm tagı henüz bağlanmadı (kasıtlı).

### 2026-09-21 — PLC-HMI-20260921-09: manuel bıçak/baskı Aşağı talepleri (tamamlandı, online test bekliyor)
Kaynak: `.ai/HMI_MANUAL_DOWN_REQUESTS_20260921.md`. PLC ST teslimi hazır;
`xBladeDownRequest`/`xClampDownRequest` PLC'de henüz build/export/online
doğrulanmadı - bu yüzden bu ikisi ve `xAlarmStopRequest`/`xManualPreparation
Required` yalnız `config/opcua.example.json`'a eklendi, GERÇEK yerel
`config/opcua.json`'a eklenmedi (canlı bağlantıyı riske atmamak için).
`xEmergencyOK`/`xMotionStop`/`FeedForwardPB`/`FeedReversePB` 2026-09-18
GVL kaynağında zaten doğrulanmış tag'ler olduğu için gerçek config'e de
eklendi.
- [x] Dört BOOL pulse buton artık ortak, daha eksiksiz bir izin kontrolünden
      geçiyor (`MachineService._pneumatic_common_allowed`): MANUAL state +
      xManualMode + xEmergencyOK + NOT xAlarmStopRequest + NOT xMotionStop +
      eksenler durmuş (X ve Y) + jog bırakılmış. Yukarı (Retract) da bu
      kontrole taşındı (eskiden daha gevşek `_manual_allowed` kullanıyordu).
- [x] Aşağı için ek şart: xManualPreparationRequired FALSE + fiziksel besleme
      pushbuttonları/komutu kapalı - hazırlıkta Yukarı serbest, Aşağı pasif.
- [x] Aynı mekanizmanın Yukarı pulse'u "iş başında" sayıldığı pencerede
      (command_pulse_ms) Aşağı reddedilir (Yukarı öncelikli); mekanizmalar
      (bıçak/baskı) birbirinden bağımsız.
- [x] Aşağı'ya PLC-onaylı bir "kabul" biti YOK (bilinçli tasarım) - Manuel
      sayfada "Son Komut" kartı Yukarı için PLC kabulünü, Aşağı için yalnız
      "gönderildi"yi (kanıt değil) ayrı ayrı gösterir; Sensör kartı tek
      fiziksel kanıt kalıyor.
- [x] Testler: `tests/test_manual_down_requests.py` (26). Tam suite 204/204.
      Gerçek PLC'ye kendi kendine yazılmadı/hareket başlatılmadı.
- [x] Kullanıcı: PLC tarafını build/export edip online sembolleri
      doğruladıktan sonra 4 yeni NodeId'yi (`cmd_blade_down`,
      `cmd_clamp_down`, `alarm_stop_request`, `manual_preparation_required`)
      gerçek `config/opcua.json`'a eklemeli - HMI şimdilik bunları yazmıyor.

### 2026-09-21 — C0.4 takip: gerçek config eşlemesi + eksik-tag koruması (tamamlandı)
Kullanıcı: "C0.4 aşağı butonlarının bağlantısı gerçek config/opcua.json
dosyasında eksik... PLC'de yeni request'lerin Symbol Configuration üzerinden
yayımlandığını doğrulayarak ... eşlemeleri tamamla." PLC tarafı 4 tag'i
(xBladeDownRequest/xClampDownRequest/xAlarmStopRequest/xManualPreparation
Required) online doğruladı - yukarıdaki `[ ]` `[x]`'e çevrildi, 4 NodeId
gerçek `config/opcua.json`'a eklendi.
- [x] `MachineService.blade_down_tags_configured()`/`clamp_down_tags_
      configured()` (demo modda her zaman True) - Aşağı butonları artık
      kendi pulse tag'i + paylaşılan `alarm_stop_request`/`manual_
      preparation_required` okumaları config'te YOKSA hem devre dışı kalır
      hem tıklansa bile hiçbir pulse göndermez (`request_blade_down`/
      `request_clamp_down` artık bool döner - UI yalnız gerçekten
      gönderildiyse "GÖNDERİLDİ" gösterir, iyimser değil).
- [x] Gerçek OPC UA yazma reddi artık UI'ya taşınıyor: yeni `MachineService.
      commandWriteError` sinyali (`_on_error`, `PNEUMATIC_COMMAND_TAGS`
      eşleşmesiyle) - `manual_page.py` bunu "Son Komut" kartında "HATA — PLC
      REDDETTİ" olarak gösterir + `QMessageBox.warning` açar. Yalnız demo
      testi değil, gerçek `_write_checked` reddi (örn. BadNodeIdUnknown) bu
      yolla görünür hale geldi.
- [x] Devre dışı Aşağı butonlarında dinamik tooltip - hangi tag(ler)in
      henüz online doğrulanmadığını söyler.
- [x] Valf komutlarına (`xBladeValveCmd`/`xClampValveCmd`) hâlâ hiç
      yazılmıyor - değişmedi.
- [x] Testler: `test_manual_down_requests.py` 26 -> 33 (eksik-tag +
      commandWriteError testleri eklendi). Tam suite 211/211.

### 2026-09-21 — PLC-HMI-20260921-10/11 (C5): "Başlangıç Konumuna Dön" tek buton, 3s basılı tutuş (tamamlandı, online test bekliyor)
Kaynak: `.ai/HMI_C5_MOVE_TO_START_20260921.md` (10, aday sözleşme) + `.ai/
HMI_C5_HOLD_BUTTON_20260921.md` (11, kullanıcı UI talebi - H5-HOLD-T01..T08
test listesi dahil). C5 PLC tarafında henüz build/test edilmedi - node'lar
yalnız `config/opcua.example.json`'a eklendi, GERÇEK `config/opcua.json`'a
EKLENMEDİ (önceki C0.4 dersiyle tutarlı: online doğrulanmamış node canlı
bağlantıyı riske atabilir).
- [x] Eski "MERKEZE GİT / Y=0" (yalnız Y) butonu TAMAMEN kaldırıldı, yerine
      tek "Başlangıç Konumuna Dön" (X+Y) `HoldButton`'ı geldi - alt metin
      hedefleri (ayarlı X başlangıç/Y merkez) gösterir. `MachineService.
      y_center()`/`cmd_y_center` koda dokunulmadı (hâlâ geçerli PLC
      sözleşmesi, yalnızca artık hiçbir butona bağlı değil).
- [x] 3 saniye kesintisiz basılı tutuş: `ManualPage` içinde tek-atışlı
      `QTimer` + 100ms'lik görünür geri sayım. Erken bırakma/pointer
      butondan çıkma/pencere odağı kaybı/sayfa değişimi/izin kaybı/stale/
      bağlantı kaybı - hepsi anında iptal eder, kuyruklanmış gecikmeli
      hareket yok. Süre TAM dolunca (parmak hâlâ basılı olsa bile) TEK
      pulse; aynı basış ikinci bir sayaç/pulse üretemez.
- [x] "İzin HMI'da yeniden üretilmez" - bıçak/baskı'daki gibi ayrıntılı bir
      ön koşul listesi burada TEKRARLANMAZ, yalnız PLC'nin kendi
      `xMoveToStartAllowed`'ı okunur (`MachineService.move_to_start_allowed_
      now()`).
- [x] "Yeni isteğin readback geçişlerini izle, belirsizse tamamlandı iddia
      etme": `_update_move_to_start_status` - bir pulse gönderildikten sonra
      ya Busy TRUE görülmeli ya da Done/Aborted/Error'ın üçü de FALSE
      görülmeli (PLC eski latch'i temizledi); ancak o noktadan sonra bir
      Done/Aborted/Error TRUE'su BU isteğin sonucu sayılır - önceki başarılı
      hareketten kalma stale/latched Done asla yeni komutun sonucu
      sayılmaz. Zaten-hedefte hızlı tamamlanma (Busy hiç gözlenmeden) de
      doğru işleniyor.
- [x] Gerçek OPC UA yazma reddi (`commandWriteError`, `cmd_move_to_start`)
      "sent" durumunda sonsuza kadar asılı kalmayı önler - doğrudan "error"a
      geçer.
- [x] Busy, `xCycleActive` DEĞİL - bu yüzden HMI Busy'yi AYRICA kilitler:
      jog (`_manual_allowed`), mod değişimi (`_mode_change_allowed`),
      bıçak/baskı dört buton (`_pneumatic_common_allowed`) ve Ayarlar
      parametre yazmaları (`set_parameter`, `ValueError` fırlatır). Stop
      (`request_stop`) hiçbir zaman kilitlenmez.
- [x] Eksik NodeId/bağlantı/stale'de buton hiç etkinleşmez
      (`move_to_start_tags_configured()`), dinamik tooltip nedenini söyler.
- [x] Testler: `tests/test_move_to_start.py` (24, servis katmanı - izin,
      gönderim, edge-detection, busy-kilitleri, demo tam döngü). UI'daki
      gerçek-zamanlı 3s sayaç davranışı widget smoke testiyle ayrıca
      doğrulandı (erken bırakma, tam 3s, basılı kalırken ikinci pulse yok).
      Tam suite 235/235. Gerçek PLC'ye kendi kendine yazılmadı/hareket
      başlatılmadı - H5-HOLD-T08 (fiziksel hareket) kullanıcıyı bekliyor.

### 2026-09-21 — Manuel sayfa UI geri bildirimi: yerleşim/hizalama/jog hızı girişi (tamamlandı)
Kullanıcı ekran görüntüsüyle 4 istek iletti (bkz. CHANGELOG_MEMORY.md aynı
tarihli en üst giriş için tam gerekçe).
- [x] "Başlangıç Konumuna Dön" X Ekseni kartına taşındı (eski boş spacer'ın
      yerine); "BAŞLANGIÇ KONUMU" durum kartı Y Ekseni kartında kaldı.
      Hint metni artık butonun kendi içinde (`HoldButton` üzerine
      `QVBoxLayout`), sağ-alt köşede.
- [x] X-/X+ ile Y-/Y+ hizası: her iki kartın `body_layout()`'una `addStretch
      (1)` eklendi - kök neden (kartlar eşit yüksekliğe zorlanıyordu ama
      hiçbiri kendi içinde stretch kullanmıyordu) düzeltildi.
- [x] "JOG Yavaş/Hızlı" (gerçek modda zaten etkisizdi) kaldırıldı; yerine
      `lr_x_jog_velocity`/`lr_y_jog_velocity` ayar parametresine bağlı,
      "Düzenle" tik kutusuyla kilitli `QDoubleSpinBox`. Kilit açıkken
      `editingFinished`'da `MachineService.set_parameter()` (Ayarlar'la AYNI
      yol) çağrılır; Ayarlar'daki "dirty" deseni birebir tekrarlandı. Demo
      simülatörünün jog hızı da artık bu parametreden okunuyor.
- [x] `jog_x`/`jog_y`/`DemoSimulator.set_jog_x`/`set_jog_y`'den etkisiz
      `fast` parametresi tamamen kaldırıldı.
- [x] Testler: mevcut 235 test aynen geçti. Yeni davranış (kilit aç/kapa,
      dirty-commit, geçersiz değer reddi) + hizalama widget smoke testi ve
      gerçek render edilmiş ekran görüntüsüyle doğrulandı.

### 2026-09-21 — PLC-HMI-20260921-12: C5 gerçek config eksiği (tamamlandı)
Kullanıcı PLC üzerinde elle `xMoveToStartRequest`i TRUE yazıp iki eksenin
hedefe gittiğini doğruladı - C5 online teyit edilmiş oldu. PLC kod
incelemesi: buton mantığı zaten doğruydu, eksik olan yalnızca 6 NodeId'nin
gerçek `config/opcua.json`'a hiç eklenmemiş olmasıydı (önceki turda C5
henüz online doğrulanmadığı için kasıtlı bırakılmıştı).
- [x] `cmd_move_to_start`, `move_to_start_allowed/busy/done/aborted/error`
      -> `GVL.xMoveToStartRequest/Allowed/Busy/Done/Aborted/Error`,
      `config/opcua.example.json` ile birebir aynı, gerçek `config/opcua.
      json`'a eklendi (namespace/path tahmin edilmedi).
- [x] Eksik tag durumunda "Başlangıç Konumu" kartı artık "—" değil "TAG
      EKSİK" (fault) gösteriyor - PLC notu: "boş tireyle bırakma."
- [x] Basitlik korundu - yeni katman/ekran/state yok, yalnızca config +
      bir metin dallanması. `move_to_start_allowed_now()` hâlâ yalnız
      PLC'nin `xMoveToStartAllowed`'ını okuyor.
- [x] Kullanıcıya/PLC tarafına iletildi: PLC'de elle TRUE bırakılan
      `xMoveToStartRequest` önce FALSE'a çekilmeli - HMI pulse'u zaten-TRUE
      bitten yeni bir yükselen kenar oluşturmayabilir.
- [x] Testler: mevcut 235 test aynen geçti. Gerçek config'in 6 anahtarı
      içerdiği + dolu/eksik config senaryoları widget smoke testiyle
      doğrulandı. Gerçek PLC'ye bağlı bir bağlantımız yok - butonun uçtan
      uca çalıştığını onaylamak kullanıcının sıradaki adımı.

### 2026-09-21 — PLC-HMI-20260921-14/15/16: Hata/Uyarı/Mesaj kataloğu + Reset bug fix (tamamlandı)
Kaynak: `.ai/HMI_C5_ALARM_MESSAGES_20260921.md` + `.ai/HMI_C6_NOTIFICATION_
CLASSES_20260921.md` + `.ai/C6_ALARM_WARNING_MESSAGE_CATALOG_20260921.md`.
- [x] **Bug fix:** `request_reset()` gerçek modda artık `_alarms.clear_
      active()` çağırmıyor - Reset kabul edilmeden aktif HATA kaybolmuyor.
- [x] `MachineService.ALARM_CATALOG`/`_update_alarm_conditions` - H01-H18
      (confirmed tag'lerle) + H19 (FAULT fallback, çift saymadan) rising/
      falling edge ile `AlarmRepository`'ye yazılıyor/kapatılıyor.
      H12-H15 (5 aday tag) kod hazır, yalnız example config'te - PLC
      build/export bekleniyor.
- [x] `active_alarm_count()` - ana ekran ALARM sayacı artık hayali `snap.
      alarm_count` değil, gerçek aktif HATA listesinden.
- [x] `compute_start_inhibit_reasons` yeniden yazıldı - artık ilk engelde
      return etmiyor, U01-U11 tüm geçerli UYARI'ları birlikte listeliyor;
      stale kendi UYARI'sını gösteriyor (eskiden sessizce boştu); aktif
      çevrimde hiç UYARI yok (normal durum).
- [x] Manuel sayfa: move-to-start için "stopping" (Busy+Aborted) durumu
      eklendi, terminal sonuçta Error önceliği; H05 alarm mesajı mesaj
      14'teki tam yönlendirme metnini içeriyor.
- [x] Yan bulgu: yerel `data/bufera.db`'de `code` sütunu hâlâ fiziksel
      NOT NULL'dı (model nullable tanımlasa da) - tablo yeniden kurularak
      (veri kaybı yok) düzeltildi.
- [x] Testler: `test_alarm_catalog.py` (11, yeni), `test_start_inhibit_
      reasons.py` (19, yeniden yazıldı), `test_alarm_severity.py` (+1),
      `test_move_to_start.py` (+1). Tam suite 256/256.

### 2026-09-22 — Alarmlar sayfası: "Alarm Listesi" sekmesi + sekme metni okunmuyordu (tamamlandı)
Kullanıcı ekran görüntüsü: "Güncel/Geçmiş Alarmlar" sekme metinleri arka
fonla aynı renkte, okunmuyordu; ayrıca operatörün alarm anlamlarını
okuyabileceği bir liste istendi.
- [x] `theme.py`'ye `QTabWidget`/`QTabBar` stil kuralları eklendi (daha
      önce hiç yoktu - Qt'nin varsayılan açık renk sekme çizimi koyu
      temanın açık metin rengiyle çakışıyordu).
- [x] Yeni `core/notification_catalog.py` - CANLI veri okumayan statik
      referans, `ALARM_CATALOG` (H01-H19) ve `compute_start_inhibit_
      reasons` (U01-U11) ile birebir aynı metinler + M01-M09 (durum
      mesajları). Alarmlar sayfasına üçüncü "Alarm Listesi" sekmesi olarak
      eklendi (Kod/Tür/Ne Zaman Görünür/Anlamı sütunları).
- [x] Testler: `test_notification_catalog.py` (4, yeni - veri bütünlüğü).
      Tam suite 260/260. Gerçek render edilmiş ekran görüntüsüyle
      doğrulandı (sekme metni okunur + katalog tablosu doğru).

### 2026-09-22 — PLC-HMI-20260922-17: C6 toplu teslim, H20/H21/H22 (tamamlandı)
Kaynak: `.ai/HMI_C6_FINAL_TASK_20260922.md`. 3 yeni aday latched HATA - PLC
kod/test teslim etti ama build/online doğrulama henüz yapılmadı.
- [x] `MachineSnapshot`'a 3 yeni RO alan (`alarm_mode_changed_during_cycle`/
      `alarm_clamp_lost_during_cycle`/`alarm_blade_not_clear_during_
      return`), varsayılan False.
- [x] `ALARM_CATALOG`'a H20/H21/H22 - aynı rising/falling edge motoru,
      metinler görev dosyasıyla birebir.
- [x] 3 tag yalnız `config/opcua.example.json`'a (H12-H15 ile aynı
      disiplin - PLC online doğrulayana kadar gerçek config'e girmez).
- [x] "Alarm Listesi" sekmesine H20-H22, "henüz build/online doğrulama
      yapılmadı" notuyla eklendi.
- [x] Testler: `test_alarm_catalog.py` (+2 - initial/rising/falling/
      history + reset-reddi üçü için), `test_notification_catalog.py`
      (H01-H22 kapsama güncellendi). Tam suite 262/262.

### 2026-09-22 — U01-U11 alarm tablosuna canlı satır olarak eklendi (kullanıcı sorusu, tamamlandı)
Kullanıcı: "U10 bir uyarı, neden tabloda değil? kodu da görünmüyor."
Gerçek bulgu: `SEVERITY_WARNING` hiç `AlarmRepository`'ye yazılmıyordu,
ana ekran "Uyarı" filtresi pratikte hep boştu.
- [x] `compute_start_inhibit_reasons` her nedeni `[Uxx]` koduyla döndürüyor
      (`ui/machine/machine_page.py`).
- [x] `MachinePage._on_snapshot` artık `_live_warning_messages`'ı her
      tick'te güncelleyip `_refresh_alarm_table()`'ı çağırıyor; "Uyarı"
      işaretliyken bu CANLI satırlar ("ŞİMDİ"/PLC/[Uxx]) gerçek HATA
      satırlarıyla aynı tabloda görünüyor. Kullanıcı isteği gereği
      `AlarmRepository`'ye YAZILMIYOR - Reset'ten bağımsız, geçmişte iz
      bırakmıyor, koşul kapanınca anında kayboluyor (alarm yağmuru
      hedefi korunuyor).
- [x] Testler: `test_start_inhibit_reasons.py` (kod önekleri için literal
      güncellemeler), `test_machine_page_warning_table.py` (5, yeni).
      Tam suite 267/267. Gerçek render edilmiş ekran görüntüsüyle
      doğrulandı.

### 2026-09-22 — Manuel sayfa: "Başlangıç Konumuna Dön" satırı yamuktu (kullanıcı ekran görüntüsü, tamamlandı)
Kullanıcı: "sıfıra gönder butonu ile başlangıç konumu yanyana ama aynı
yükseklikte değil... genişliği farklı. Bu da sayfada yamukluk yaratıyor."
- [x] Kök neden widget geometrisiyle doğrulandı: X kartındaki buton
      (`HoldButton`, sabit `PRIMARY_ACTION_HEIGHT=64`) ile Y kartındaki
      karşılığı (`ProcessStatusCard`, doğal içerik yüksekliği=72) 8px
      farklıydı - kart GENİŞLİKLERİ zaten birebir eşitti, sorun bu satırdan
      sonraki her şeyin (Actual Position, Servo) X/Y arasında kaymasıydı.
- [x] `ManualPage._build_ui`'de her iki axis kartı kurulduktan sonra
      `_move_to_start_status.sizeHint().height()` okunup hem butona hem
      duruma `setFixedHeight` ile uygulanıyor - artık garantili eşit.
- [x] Saf layout/geometri düzeltmesi, davranış değişmedi - yeni test
      gerekmedi. Gerçek render + widget `.geometry()` ölçümüyle doğrulandı
      (önce 64/72, sonra 72/72; alttaki satırlar piksel piksel hizalı).
      Tam suite 267/267 (değişmedi).

### 2026-09-22 — PLC-HMI-20260922-18: C06_1 HMI kaynak denetimi, A01-A06 (tamamlandı)
Kaynak: `.ai/HMI_C061_AUDIT_TASK_20260922.md` - başka bir ajanın bağımsız
kaynak denetimi. Her madde kodda doğrulandıktan sonra uygulandı (hiçbiri
uydurma değildi); A06'daki iki etiket önceki oturumlarda attığım gerçek
hatalardı. Detay: `CHANGELOG_MEMORY.md` üst giriş.
- [x] A01 (P1): `set_parameter` artık ortak `_settings_write_allowed()`
      kapısından geçiyor - stale/bağlantı (gerçek modda) + cycle_active +
      jog + eksen hareketi. Eskiden yalnız move_to_start_busy vardı.
- [x] A02 (P1): restart sonrası alarm uzlaştırması - yeni `AlarmEvent.
      catalog_id` (migration), `_reconcile_alarm_state_with_persisted_
      events()`. Aktif sayaç/liste artık sınırsız (`active_events()`),
      eskiden `recent(limit=100)`'e bağlıydı.
- [x] A03 (P2): `compute_start_inhibit_reasons` stale kontrolü artık
      start_permitted'den ÖNCE (eski sırada bayat+eski-TRUE-izin
      kombinasyonunda U10 hiç görünmüyordu).
- [x] A04 (P1 entegrasyon kapısı): Alarmlar sayfasında dinamik "online
      doğrulama bekleyen kodlar" banner'ı - `pending_candidate_catalog_
      ids()`, config'ten canlı okur (H06/H07'nin türetilmiş config
      anahtarı için özel eşleme gerekti).
- [x] A05 (P2): M01-M09 artık ana ekran tablosunda canlı
      (`compute_active_state_message`); M08 edge-tabanlı (yalnız
      move_to_start "done" olduğu ilk tick, tek seferlik).
- [x] A06: state 140 "Durduruluyor" (PLC'nin 13 numaralı bulgusuyla
      uyumlu), 510 "Manuel Hazırlık Bekleniyor" (PLC'nin 2026-09-18
      talimatı - "Recovery" kelimesi kullanılmamalıydı); pnömatik ortak
      izne operator_stop_active eklendi; U05/"build-export" yorum
      düzeltmeleri.
- [x] Yan bulgu: `data/bufera.db`'deki eski kod=1201 alarmları GERÇEK
      değil - `DemoSimulator`'ın kendi test-yan-etkisi (önceki oturumda
      yanlışlıkla "gerçek geçmiş" sanılıp korunmuştu).
- [x] Testler: `test_settings_write_permission.py` (8, yeni), `test_
      alarm_restart_reconciliation.py` (6, yeni), `test_active_state_
      message.py` (10, yeni), `test_machine_page_message_table.py` (5,
      yeni), + `test_alarm_catalog.py`/`test_cycle_state.py`/`test_
      manual_down_requests.py`/`test_start_inhibit_reasons.py` güncellemeleri.
      Tam suite 305/305.

### 2026-09-22 — Hız parametre sınırları gerçek mekaniğe göre revize edildi (kullanıcı talebi, tamamlandı)
Kullanıcı: "HIZ SINIRLARINI BU ŞEKİLDE REVİZE ET MEKANİĞE BAĞLANDIK VE BU
SINIRLARA KARAR VERDİK" - artık tahmin değil, onaylı nihai mekanik limit.
- [x] `core/parameters.py`: X Kesim Hızı 1-800, X Dönüş Hızı 1-1060,
      Y Pozisyonlama Hızı 1-50, Y Follow Maks. Hızı 1-50, X Jog Hızı
      1-400, Y Jog Hızı 1-50. Tüm `default` değerleri yeni aralıkta kaldı,
      değiştirilmedi.
- [x] Test: `test_parameters.py::test_velocity_ranges_match_confirmed_
      mechanical_limits` (yeni, regresyonu kilitler). Demo modda uç
      değerler + bir üstü (reddedilmeli) elle doğrulandı. Tam suite 306/306.

### 2026-09-23 — PLC-HMI-20260923-20: C8 "Sıfır Referansı Belirle" (sade sürüm, tamamlandı)
Kaynak: `.ai/HMI_C8_SADE_SURUM_20260923.md` (19 numaralı 10-tag/EMG-
geçmişi paketi İPTAL edilmişti). Kullanıcı: "C8 e geçelim o istekleri
tamamlayalım." Detay: `CHANGELOG_MEMORY.md` üst giriş.
- [x] 10 yeni RO alan (`x_home_*`/`y_home_*`, mevcut MC_Home FB üyeleri)
      + tek RW `cmd_set_zero_request` - config'te eşleme olmadığı sürece
      hep False (C0.4/C5 disiplini, NodeId yolu TAHMİN - PLC teyidi istendi).
- [x] `_set_zero_common_allowed()`, `request_set_zero()` (LEVEL yazma),
      `_update_set_zero_status()` - C5'teki "cleared" deseni + bağlantı
      kaybında donma/reconnect'te TRUE tekrar göndermeme + 15sn zaman
      aşımı. `_manual_allowed()`'a jog kilidi eklendi.
- [x] `ui/machine/set_zero_dialog.py` (yeni) - şifreli, uygulama-genelinde
      MODAL, 3sn `HoldButton`, işlem sürerken kapatılamaz.
      `settings_page.py`'ye giriş düğmesi (Vision Sim'le aynı şifre).
- [x] Demo modda tam simülasyon (`demo_simulator.py::_apply_set_zero`).
- [x] Bilinçli kapsam: "Alarm Listesi" kataloğuna eklenmedi (H-kodu=kalıcı
      alarm kuralını bozmamak için), pnömatik butonlar set-zero sürerken
      kilitlenmedi (görev dosyası yalnız jog/feed formülüne dokunuyor).
- [x] Testler: `test_set_zero_reference.py` (26, yeni), `test_set_zero_
      dialog.py` (14, yeni). Tam suite 346/346. Gerçek render + demo 50ms
      tick döngüsüyle uçtan uca (hazır→basılı tutma→işlem sürüyor→X/Y=0/
      başarı) doğrulandı.

### 2026-09-23 — C8: sahada test + gerçek PLC browse doğrulaması + iki UI hata düzeltmesi (tamamlandı)
Kullanıcı sahada test etti, buton pasif kaldı. Detay: `CHANGELOG_MEMORY.md`
üstteki 2 giriş.
- [x] Diyalog TAG EKSİK durumunda yanlış "manuel/servo/mekanizma kontrol
      edin" metni gösteriyordu - düzeltildi.
- [x] Kendi hatam: "PLC henüz online doğrulamadı" diye KANITSIZ bir neden
      yazmışım (PLC-HMI-20260923-23 ile düzeltildi). Gerçek `opc.tcp://
      192.168.0.2:4840`'a salt-okunur `asyncua.Client` ile bağlanıp
      browse/read yaptım: `xSetZeroRequest` CANLI doğrulandı (gerçek
      config'e eklendi, yedekli) - 10 MC_Home RO alanı `BadNodeIdUnknown`
      (`Motion_Control` online sembol ağacında yok).
- [x] `set_zero_missing_tags()` (yeni) - diyalog/tooltip artık "PLC kodu
      yüklenmedi" iddiası yapmayan nötr metin + gerçek eksik alan listesi
      gösteriyor.
- [x] Testler: +3/+1 güncelleme. Tam suite 350/350.

### 2026-09-23 — C8 TAMAMLANDI: 11/11 tag gerçek config'te, buton gerçek makinede aktif (tamamlandı)
Kullanıcı UaExpert ekran görüntüsü paylaştı - kalan 10 RO alan bir önceki
browse'dan SONRA indirilmiş, artık canlı. Detay: `CHANGELOG_MEMORY.md`
üst giriş.
- [x] İkinci salt-okunur browse: GVL 155→165 (+10). Gerçek isimler
      `xX_HomeDone/Busy/Aborted/Error`, `eX_HomeErrorID` (X) + `xY_Home...`,
      `eY_HomeErrorID` (Y) - GVL düz değişkenler, `Motion_Control.*` FB
      üyesi tahminim YANLIŞTI.
- [x] `config/opcua.json`'a kalan 10 alan doğru isimlerle eklendi (11/11
      tamam), `config/opcua.example.json` düzeltildi.
- [x] Test fixture NodeId'leri düzeltildi (bir sed komutu `.Error`/
      `.ErrorID` pattern çakışmasıyla 2 satırı yanlış yazmıştı - fark
      edilip düzeltildi).
- [x] Gerçek render edilmiş ekran görüntüsüyle doğrulandı: "Koşullar
      sağlanıyor.", buton aktif. Tam suite 350/350. Sahada gerçek homing
      denemesi henüz yapılmadı (kullanıcı yapacak).
