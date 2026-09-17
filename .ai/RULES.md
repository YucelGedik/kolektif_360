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
- Son build/test: 2026-09-12 - `pytest` 8/8 gecti, uygulama gercekten
  calistirilip ekran goruntuleriyle dogrulandi (bkz. CHANGELOG_MEMORY.md).

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

### 2026-09-17 — Kullanıcı önceliği: geçici Vision simülatörü
- [ ] .ai/HMI_TEMP_VISION_SIMULATOR_TASK.md Faz 0: sözleşme/kaynak farkları.
- [ ] Faz 1: varsayılan kapalı özellik, mühendislik erişimi, yazıcı sahipliği.
- [ ] Faz 2: sıralı paket ve bağımsız heartbeat.
- [ ] Faz 3: ana HMI'yi değiştirmeyen geçici diagnostic sayfa.
- [ ] Faz 4: kapanış/reconnect ve gerçek kameraya çakışmasız geçiş.
- [ ] Faz 5: izole testler, regresyon ve kullanıcı test rehberi.
Bu alt fazlar mevcut Vision Simulator işinin ayrıntısıdır; ayrı kalıcı operatör işlevi değildir.
