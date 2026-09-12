# Bufera Makine Ekranı - Teknik Hafiza

Bu dosya proje hakkinda kalici teknik referanstir. Oturum basinda komple
okunmaz; sadece ihtiyac aninda ilgili bolumu okunur.

## Proje Ozeti

- Proje: Bufera Makine Ekranı - perde/kumas boylamasina kesim makinesinin
  operator/manuel/muhendislik/alarm kontrol ekranlari.
- VisionCut (kamera + Y ekseni sapma telafisi yapan mevcut uygulama) baska
  bir sirkete ait; kaynak kodu paylasilmiyor. Bu repo VisionCut'a sonradan
  entegre edilecek bagimsiz bir teslim paketidir (bkz. `INTEGRATION.md`).
- Stack: Python 3.13.15, PySide6 6.11.1, asyncua >=1.1, pydantic 2.13.4,
  SQLAlchemy >=2.0, SQLite, pytest.
- OpenCV/NumPy BILEREK disarida birakildi: kamera/goruntu isleme VisionCut'in
  isi, makine ekraninin buna ihtiyaci yok.
- Ana kaynak dizini: proje koku (`core/`, `plc/`, `services/`, `persistence/`,
  `ui/machine/`, `app/`).
- Build: `python -m venv .venv` + `pip install -r requirements.txt`
- Run: `.venv\Scripts\python.exe -m app.main`
- Test: `.venv\Scripts\python.exe -m pytest`

## Dizin Haritasi

```text
core/
  cycle_state.py     CycleState IntEnum + Turkce etiketler (brif SS14)
  models.py          MachineSnapshot dataclass(slots=True) (brif SS19 genisletilmis)
  parameters.py      PARAMETER_SPECS (muhendislik parametre limitleri, brif SS8/13/24)
plc/
  models.py          OpcUaConfig (pydantic) - endpoint, nodes, timeout'lar
  tag_map.py         config/opcua.json yukleme + TagMap (isim -> NodeId)
  opcua_client.py    OpcUaWorker(QThread) - asyncua, batch read, pulse write, reconnect
services/
  machine_service.py MERKEZI servis - tum UI sayfalari bunun uzerinden gecer
  demo_simulator.py  DemoSimulator - PLC yokken tam cevrim + alarm simulasyonu
persistence/
  db.py              SQLAlchemy engine/session (SQLite, data/bufera.db)
  alarms.py          AlarmEvent modeli + AlarmRepository (brif SS9 kod araligi)
  settings_store.py  Muhendislik parametre override kaydi
ui/machine/
  theme.py           VisionCut renk/font tokenlari (brif SS31, birebir)
  widgets.py         Card, Readout, StatusChip, ProcessStatusCard, HoldButton, SectionTabs
  machine_page.py    Ekran A - Operator (brif SS8-A, SS21, SS22)
  manual_page.py     Ekran B - Manuel/Servis (brif SS8-B)
  settings_page.py   Ekran C - Ayarlar/Muhendislik (brif SS8-C, SS13, SS24)
  alarm_page.py      Alarm listesi (brif SS9)
app/
  main.py            Bagimsiz gelistirme/demo kabugu (VisionCut'in kendisi DEGIL)
config/
  opcua.example.json Referans node mapping (git'te), IPC_Y_POS test tagi dahil
  opcua.json         Gercek/lokal config (gitignore'lu, endpoint bos = Demo mod)
tests/
  test_tag_map.py, test_cycle_state.py
docs/
  BUFERA_MAKINE_EKRANI_CODEX_ENTEGRASYON_BRIFI.md   32 bolumluk orijinal brif
```

## Veri Akisi

```text
Gercek PLC modu:
  PLC (CODESYS/MAT LC-C07) --OPC UA--> OpcUaWorker (QThread, asyncua)
    --Qt signal (raw dict)--> MachineService._on_raw_snapshot()
    --MachineSnapshot cache--> QTimer (50ms) --snapshotUpdated signal--> UI sayfalari

Demo modu (config/opcua.json endpoint bos):
  DemoSimulator.tick() (50ms) --MachineSnapshot'i dogrudan mutate eder-->
    ayni QTimer --snapshotUpdated signal--> UI sayfalari

Komutlar (Start/Stop/Reset/Jog/Blade/Clamp):
  UI --MachineService.request_*/jog_*/set_*()--> ya OpcUaWorker.request_pulse/write()
    (gercek mod) ya da DemoSimulator ilgili metodu (demo mod)
```

UI hicbir zaman PLC/demo ayrimini bilmez; sadece `MachineService` API'sini
cagirir ve `snapshotUpdated`/`connectionStateChanged`/`alarmsChanged`
sinyallerini dinler.

## Onemli Moduller

| Modul | Gorev | Not |
|-------|-------|-----|
| `services/machine_service.py` | Tek merkezi servis, gercek/demo ayrimini gizler | Her sayfa BUNU kullanir, dogrudan `opcua_client` degil (brif SS26) |
| `plc/opcua_client.py` | UI thread'i bloklamayan OPC UA worker | Reconnect state machine: Disconnected/Connecting/Connected/Degraded/Error |
| `services/demo_simulator.py` | Gercek PLC olmadan tam cevrim simulasyonu | 8 saniyelik idle sonrasi otomatik demo alarm (1201 Vision Heartbeat) |
| `core/cycle_state.py` | Tek dogru kaynak: CycleState kodlari + TR metin | UI hicbir yerde ham int gostermez |
| `persistence/alarms.py` | SQLite alarm gecmisi | Uygulama yeniden baslasa da alarm gecmisi kalir |

## Entegrasyonlar

| Entegrasyon | Durum | Not |
|-------------|-------|-----|
| OPC UA / MAT LC-C07 PLC | Config hazir, gercek PLC ile test edilmedi | Ilk test tagi: `ns=4;s=\|var\|MAT LC-C07.Application.GVL.IPC_Y_POS` |
| VisionCut (harici uygulama) | Entegrasyon YOK, sadece teslim planlaniyor | Kaynak kod paylasilmiyor; bkz. `INTEGRATION.md` |
| GitHub (`YucelGedik/kolektif_360`) | Push edildi (`master`) | Uzak repo aciklamasi: "Camera-assisted curtain cutting project" |

## Riskli Alanlar

- `plc/opcua_client.py` write'larinda VariantType asyncua tarafindan otomatik
  cikariliyor; gercek PLC'de `BadTypeMismatch` cikabilir (brif SS28).
- JOG Yavas/Hizli secimi icin PLC tarafinda henuz tag yok; sadece demo modda
  etkili (`services/machine_service.py::jog_x/jog_y` icinde not var).
- CycleState numeric kodlari PLC tarafi henuz kesinlesmedi (brif SS28);
  `core/cycle_state.py` tek degisim noktasi olacak sekilde tasarlandi.
- `ui/machine/theme.py` ve `widgets.py` VisionCut'in GERCEK bileşenleri
  DEGIL, bizim tahmini setimiz - entegrasyonda VisionCut'in kendi
  component'leriyle degistirilmesi gerekebilir.
